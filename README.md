# Binary crates cache

This repository is responsible for building and persisting binary crates cache,
which is used later by [actions-rs/install](https://github.com/actions-rs/install) Action.

## Cached crates

See [workflow file](https://github.com/actions-rs/tool-cache/blob/master/.github/workflows/build.yml)
for a list of crates, which are stored in the cache storage.

If you want to suggest a new crate to be added into the crate cache,
check if it was [asked before](https://github.com/actions-rs/tool-cache/issues)  already,
and if not - [create a new issue](https://github.com/actions-rs/tool-cache/issues/new?assignees=&labels=question&template=cache_crate.md&title=).

## Security considerations

Binary crates cache is stored at the third party server (AWS S3),
meaning that using this tool cache is potentially less secure
than just calling `cargo install` command.

Pre-built binaries are executed directly in the virtual environments
and have full access to them, including access to the environment variables,
[secrets](https://help.github.com/en/actions/configuring-and-managing-workflows/creating-and-storing-encrypted-secrets),
[access tokens](https://help.github.com/en/actions/configuring-and-managing-workflows/authenticating-with-the-github_token)
and so on.

Malicious parties potentially might replace these pre-built binaries,
leading to the security breach.
We try our best to mitigate any potential security problems, 
but you must acknowledge that fact before using any @actions-rs Action,
which uses this cache internally and explicitly enabling this functionality.

### Security measures

1. Crates are compiled [right here at GitHub](https://github.com/actions-rs/tool-cache/actions?query=workflow%3A%22Build+tools+cache%22+event%3Aschedule)
2. Crates are signed with 4096 bit RSA key
3. That RSA key is stored in the [GitHub secrets](https://help.github.com/en/actions/configuring-and-managing-workflows/creating-and-storing-encrypted-secrets)
4. Actions at [@actions-rs](https://github.com/actions-rs) are validating
    this signature after the file downloading
5. Compiled crates are stored in the AWS S3 bucket and served via AWS CloudFront
6. MFA is enabled for AWS root user
7. Separate AWS user for files uploading has the console access disabled
    and only one permission: `PutObject` for this S3 bucket
8. AWS access key and other confidential details are stored in the
    GitHub secrets

Refer to the [@actions-rs/install](https://github.com/actions-rs/install)
documentation to learn more about files downloading and validating.

## Contribute and support

Any contributions are welcomed!

If you want to report a bug or have a feature request,
check the [Contributing guide](https://github.com/actions-rs/.github/blob/master/CONTRIBUTING.md).

You can also support author by funding the ongoing project work,
see [Sponsoring](https://actions-rs.github.io/#sponsoring).
