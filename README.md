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
than calling `cargo install` command.

Pre-built binaries are executed directly in the virtual environments
and have full access to them, including access to the environment variables,
[secrets](https://help.github.com/en/actions/configuring-and-managing-workflows/creating-and-storing-encrypted-secrets),
[access tokens](https://help.github.com/en/actions/configuring-and-managing-workflows/authenticating-with-the-github_token)
and so on.

Malicious parties potentially might replace these pre-built binaries,
leading to the security breach.
We try our best to mitigate any potential security problems, 
but you must acknowledge that fact before using any @actions-rs Action,
which uses this cache internally.

## Contribute and support

Any contributions are welcomed!

If you want to report a bug or have a feature request,
check the [Contributing guide](https://github.com/actions-rs/.github/blob/master/CONTRIBUTING.md).

You can also support author by funding the ongoing project work,
see [Sponsoring](https://actions-rs.github.io/#sponsoring).
