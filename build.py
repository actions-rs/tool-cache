#!/usr/bin/env python

import os
import os.path
import tempfile
import logging
import logging.config
import subprocess
import zipfile

import boto3
import requests
from dotenv import load_dotenv

# Mostly for a local testing
load_dotenv()

S3_OBJECT_URL = 'https://s3.{region}.amazonaws.com/{bucket}/{{object_name}}'.format(
    region=os.environ['AWS_S3_REGION'],
    bucket=os.environ['AWS_S3_BUCKET'],
)
S3_OBJECT_NAME = '{crate}/{runner}/{crate}-{version}.zip'
CLOUDFRONT_URL = 'https://d1ad61wkrfbmp3.cloudfront.net/{filename}'

MAX_VERSIONS_TO_BUILD = 3

# Set of crates not to be built in any condition.
EXCLUDES = {
    # https://github.com/mozilla/grcov/issues/405
    ('grcov', '0.5.10'),
}


def which(executable):
    for path in os.environ['PATH'].split(os.pathsep):
        path = path.strip('"')

        fpath = os.path.join(path, executable)

        if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
            return fpath

    # checks if os is windows and appends .exe extension to
    # `executable`, if not already present, and rechecks.
    if os.name == 'nt' and not executable.endswith('.exe'):
        return which('{}.exe'.format(executable))


def crate_info(crate):
    url = 'https://crates.io/api/v1/crates/{}'.format(crate)
    logging.info('Requesting crates.io URL: {}'.format(url))

    resp = requests.get(url)
    resp.raise_for_status()

    def predicate(v):
        if v['yanked']:
            return False

        if (crate, v['num']) in EXCLUDES:
            return False

        return True

    versions = filter(predicate, resp.json()['versions'])
    for version in list(versions)[:MAX_VERSIONS_TO_BUILD]:
        yield version['num']


def exists(runner, crate, version):
    """Check if `crate` with version `version` for `runner` environment
    already exists in the S3 bucket."""

    object_name = S3_OBJECT_NAME.format(
        crate=crate,
        runner=runner,
        version=version,
    )
    url = CLOUDFRONT_URL.format(filename=object_name)
    logging.info(
        'Check if {crate} == {version} for {runner} exists in S3 bucket at {url}'.format(
            crate=crate,
            version=version,
            runner=runner,
            url=url,
        ))
    resp = requests.head(url, allow_redirects=True)

    if resp.ok:
        logging.info(
            '{crate} == {version} for {runner} already exists in S3 bucket'.format(
                crate=crate,
                version=version,
                runner=runner,
            ))
        return True

    else:
        logging.warning(
            '{crate} == {version} for {runner} does not exists in S3 bucket'.format(
                crate=crate,
                version=version,
                runner=runner,
            ))
        return False


def build(runner, crate, version):
    root = os.path.join(
        os.getcwd(),
        'build',
        '{}-{}-{}'.format(runner, crate, version)
    )

    logging.info('Preparing build root at {}'.format(root))
    os.makedirs(root, exist_ok=True)

    args = [
        'cargo',
        'install',
        '--version',
        version,
        '--root',
        root,
        '--no-track',
        crate,
    ]
    subprocess.check_call(args)

    archive_path = '{}.zip'.format(crate)
    with zipfile.ZipFile(archive_path, 'w') as archive:
        logging.info('Creating archive at {}'.format(archive_path))
        for filename in os.listdir(os.path.join(root, 'bin')):
            logging.info('Writing {} into {} archive'.format(filename, archive_path))
            archive.write(
                os.path.join(root, 'bin', filename),
                filename,
            )

    return archive_path


def sign(path):
    openssl = which('openssl')
    if openssl is None:
        raise ValueError('Unable to find OpenSSL!')

    signature_path = '{}.sig'.format(path)

    cert_fd, cert_path = tempfile.mkstemp(prefix='cert_')
    os.write(cert_fd, os.environ['SIGN_CERT'].encode())
    os.close(cert_fd)

    args = [
        openssl,
        'dgst',
        '-sha256',
        '-sign',
        cert_path,
        '-passin',
        'env:SIGN_CERT_PASSPHRASE',
        '-out',
        signature_path,
        path,
    ]

    try:
        logging.info('Signing {} at {}'.format(path, signature_path))
        subprocess.check_call(args)
    finally:
        os.unlink(cert_path)

    if not os.path.exists(signature_path):
        raise ValueError('Signature file is missing')

    return signature_path


def upload(client, runner, crate, version, path, signature_path):
    """Upload prebuilt `crate` with `version` for `runner` environment
    located at `path` to the S3 bucket."""

    object_name = S3_OBJECT_NAME.format(
        crate=crate,
        runner=runner,
        version=version,
    )
    object_signature_name = '{}.sig'.format(object_name)

    logging.info('Uploading {path} to {bucket}/{name}'.format(
        path=path,
        bucket=os.environ['AWS_S3_BUCKET'],
        name=object_name,
    ))
    client.upload_file(path, os.environ['AWS_S3_BUCKET'], object_name)
    client.upload_file(signature_path, os.environ['AWS_S3_BUCKET'], object_signature_name)


class LogFormatter(logging.Formatter):
    def format(self, record):
        msg = record.getMessage()
        if record.levelno == logging.DEBUG:
            return '::debug::{}'.format(msg)
        elif record.levelno == logging.INFO:
            return msg
        elif record.levelno in (logging.WARN, logging.WARNING):
            return '::warning::{}'.format(msg)
        else:
            return '::error::{}'.format(msg)


if __name__ == '__main__':
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'gha': {
                '()': LogFormatter,
            },
        },
        'handlers': {
            'stdout': {
                'class': 'logging.StreamHandler',
                'formatter': 'gha',
            },
        },
        'loggers': {
            '': {
                'handlers': ['stdout'],
                'level': 'DEBUG',
            }
        }
    })

    crate = os.environ['CRATE']
    runner = os.environ['RUNNER']

    s3_client = boto3.client(
        's3',
        region_name=os.environ['AWS_S3_REGION'],
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    )

    logging.info('Building {} crate for {} environment'.format(crate, runner))
    for version in crate_info(crate):
        if not exists(runner, crate, version):
            try:
                path = build(runner, crate, version)
            except subprocess.CalledProcessError as e:
                logging.warning(
                    'Unable to build {} == {}: {}'.format(crate, version, e)
                )
            else:
                logging.info('Built {} at {}'.format(crate, path))

                signature = sign(path)
                upload(s3_client, runner, crate, version, path, signature)
