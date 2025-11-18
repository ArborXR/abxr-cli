# ArborXR CLI

This CLI tool provides commands for managing apps and files via the ArborXR API. The tool is organized into command groups: apps and files. Each group has several subcommands to perform specific operations through the command line.

## Prerequisites

Before using the CLI tool, you must perform the following:
* Python 3 installed on your system.
* An API Token for authentication
    * Login to your ArborXR Account
    * Navigate to Settings > Access Tokens
    * Create an API Access Token for your organization
* Setting the API token
    * The environment variable ABXR_API_TOKEN (or the alternative ARBORXR_ACCESS_TOKEN), or
    * The command line option --token.

## Setup

ArborXR CLI is available through PyPI. If you have `pip` installed, you can get the latest version by installing via:
```
pip install abxrcli
```

## Global Options

### The CLI tool accepts the following global options:
`-u, --url`
* Description: API Base URL
* Default: https://api.xrdm.app/api/v2 (or the value of ABXR_API_URL environment variable)

`-t, --token`
* Description: API Token for authentication
* Default: Value of ABXR_API_TOKEN (or ARBORXR_ACCESS_TOKEN)

`-f, --format`
* Description: Data output format
* Choices: json or yaml
* Default: yaml

`-v, --version`
* Description: Show the CLI tool version and exit

`-s, --silent`
* Description: Disable any terminal printing of progress bars for longer operations, like file uploads.

## Command Groups

The CLI tool is divided into multiple groups including apps, app_bundles, files, and devices. Each group has its own set of subcommands.

### Apps Commands

These commands manage app-related operations.

#### Subcommands

##### list
* Usage:
`abxr-cli apps list`
* Description: List all available apps.


##### details
* Usage:
`abxr-cli apps details app_id`
* Positional Argument:
    * `app_id`: The unique identifier of the app.
* Description: Retrieve detailed information about a specific app.


##### versions
* Usage:
`abxr-cli apps versions app_id`
* Positional Argument:
    * `app_id`: The unique identifier of the app.
* Description: List all versions available for a specific app.


##### release_channels
* Usage:
`abxr-cli apps release_channels app_id`
* Positional Argument:
    * `app_id`: The unique identifier of the app.
* Description: List all release channels associated with a specific app.


##### release_channel_details
* Usage:
`abxr-cli apps release_channel_details app_id [--release_channel_id RELEASE_CHANNEL_ID]`
* Positional Argument:
    * `app_id`: The unique identifier of the app.
* Optional Argument:
    * --release_channel_id: The identifier for a specific release channel.
* Description: Get details for a release channel of an app.

##### release_channel_set_version
* Usage:
`abxr-cli apps release_channel_set_version app_id [--release_channel_id RELEASE_CHANNEL_ID] [--version_id VERSION_ID]`
* Positional Argument:
    * `app_id`: The unique identifier of the app.
* Optional Arguments:
    * --release_channel_id: The identifier for the release channel.
    * --version_id: The version identifier to set for the channel.
* Description: Assign a specific version to a release channel.

##### upload
* Usage:
`abxr-cli apps upload app_id filename [--version VERSION] [--notes NOTES] [--release-channel-id ID | --new-release-channel-title TITLE]`
* Positional Arguments:
    * `app_id`: The unique identifier of the app.
	* `filename`: Local path of the APK/ZIP (apk+obb) file to upload.
* Optional Arguments:
	* -v, --version: Version number (note that the Uploaded APK itself can override this value).
	* -n, --notes: Release notes for the new version.
	* --release-channel-id: ID of existing release channel to associate with this version.
	* --new-release-channel-title: Title for a new release channel to create and associate with this version.
* Description: Upload a new version of an app (APK/ZIP only). To upload an app bundle with associated files, use the `app_bundles upload` command. You can optionally associate the upload with a release channel using either --release-channel-id or --new-release-channel-title (mutually exclusive).

##### share
* Usage:
`abxr-cli apps share app_id --release_channel_id RELEASE_CHANNEL_ID --organization_slug ORGANIZATION_SLUG`
* Positional Argument:
	* `app_id`: The unique identifier of the app.
* Required Options:
	* --release_channel_id: The release channel to be shared.
	* --organization_slug: The organization slug with which the app is to be shared.
* Description: Share an app with a specific organization and release channel.

##### revoke
* Usage:
`abxr-cli apps revoke app_id --release_channel_id RELEASE_CHANNEL_ID --organization_slug ORGANIZATION_SLUG`
* Positional Argument:
	* `app_id`: The unique identifier of the app.
* Required Options:
	* --release_channel_id: The release channel from which to revoke sharing.
	* --organization_slug: The organization slug from which the app sharing should be revoked.
* Description: Revoke sharing of an app from a specific organization and release channel.


### App Bundles Commands

App bundles combine an app version with associated files that should be deployed together. These commands manage the creation, upload, and management of app bundles.

**Folder Structure and Device Paths:**
The APK file and bundle folder are provided separately. Files in your bundle folder are automatically mapped to device paths under `/sdcard/`. The folder structure is preserved:
- Files in the root folder → `/sdcard/`
- Files in subfolders → `/sdcard/{subfolder_path}/`

You can optionally specify a custom base path using `--device-path` to map files under a subdirectory of `/sdcard/`.

Example (default mapping):
```
bundle-folder/
  config.json                → /sdcard/config.json
  data/
    user.json                → /sdcard/data/user.json
    cache/
      temp.dat               → /sdcard/data/cache/temp.dat
```

Example (with `--device-path myapp/config`):
```
bundle-folder/
  config.json                → /sdcard/myapp/config/config.json
  data/
    user.json                → /sdcard/myapp/config/data/user.json
```

**Hash-Based Deduplication:**
The CLI automatically detects and reuses existing builds and files based on their content hash (SHA-256 for builds, SHA-512 for files). This means:
- Uploading the same APK multiple times only stores it once
- Files that haven't changed are reused across bundles
- Only new or modified files are uploaded, saving time and bandwidth

#### Subcommands

##### upload
* Usage:
`abxr-cli app_bundles upload <app_id> <apk_path> <bundle_folder> [--version-number VERSION] [-n NOTES] [--device-path PATH] [--release-channel-id ID | --new-release-channel-title TITLE]`
* Positional Arguments:
    * <app_id>: The unique identifier of the app.
    * <apk_path>: Path to APK file.
    * <bundle_folder>: Path to folder containing bundle files.
* Optional Arguments:
    * --version-number: Version number (APK can override this value, only used for new builds).
    * -n, --notes: Release notes for the bundle.
    * --device-path: Optional device path relative to /sdcard for bundle files (e.g., "myapp/config").
    * --release-channel-id: ID of existing release channel to associate with this bundle.
    * --new-release-channel-title: Title for a new release channel to create and associate with this bundle.
* Description: Upload an APK and all bundle files from a folder, then finalize the bundle. Bundle labels are auto-generated by the system. Automatically reuses existing builds and files based on hash matching for faster uploads. You can optionally associate the bundle with a release channel using either --release-channel-id or --new-release-channel-title (mutually exclusive).

##### list
* Usage:
`abxr-cli app_bundles list <app_id> [--status STATUS]`
* Positional Argument:
    * <app_id>: The unique identifier of the app.
* Optional Arguments:
    * --status: Filter by status (pending, processing, failed, available).
* Description: List all app bundles for a specific app.

##### details
* Usage:
`abxr-cli app_bundles details <app_bundle_id>`
* Positional Argument:
    * <app_bundle_id>: The unique identifier of the app bundle.
* Description: Get detailed information about a specific app bundle.

##### resume
* Usage:
`abxr-cli app_bundles resume <bundle_id> <apk_path> <folder_path> [--device-path PATH]`
* Positional Arguments:
    * <bundle_id>: The unique identifier of the bundle to resume.
    * <apk_path>: Path to APK file (must match original).
    * <folder_path>: Path to folder containing the original bundle files.
* Optional Arguments:
    * --device-path: Device path relative to /sdcard (must match original upload if used).
* Description: Resume a failed or interrupted bundle upload. Validates that the APK, folder structure, and device path match the original bundle, then uploads any missing files and finalizes the bundle.

##### create_from_build
* Usage:
`abxr-cli app_bundles create_from_build <build_id> <bundle_folder> <app_id> [--device-path PATH] [--release-channel-id ID | --new-release-channel-title TITLE] [-s]`
* Positional Arguments:
    * <build_id>: The unique identifier of an existing app build/version.
    * <bundle_folder>: Path to folder containing bundle files.
    * <app_id>: The unique identifier of the app (needed for file deduplication).
* Optional Arguments:
    * --device-path: Optional device path relative to /sdcard for bundle files.
    * --release-channel-id: ID of existing release channel to associate with this bundle.
    * --new-release-channel-title: Title for a new release channel to create and associate with this bundle.
    * -s, --silent: Suppress progress bars and other output.
* Description: Create an app bundle using an existing build without re-uploading the APK. This is useful when you want to create multiple bundles with different file sets from the same build, or when you already have a build and just need to add files to it. Automatically reuses existing files based on hash matching. You can optionally associate the bundle with a release channel using either --release-channel-id or --new-release-channel-title (mutually exclusive).

##### update_label
* Usage:
`abxr-cli app_bundles update_label <app_bundle_id> {--label LABEL | --clear}`
* Positional Argument:
    * <app_bundle_id>: The unique identifier of the app bundle.
* Required Options (mutually exclusive):
    * --label: New label for the bundle (max 60 characters).
    * --clear: Remove the label from the bundle.
* Description: Update or remove an app bundle's label. Labels help identify different bundles for the same app. Use --label to set a new label or --clear to remove the existing label.


### Files Commands

These commands are used for file-related operations.

#### Subcommands

##### list
* Usage:
`abxr-cli files list`
* Description: List all files available.


##### details
* Usage:
`abxr-cli files details file_id`
* Positional Argument:
	* `file_id`: The unique identifier of the file.
* Description: Get detailed information for a specific file.

### Devices Commands

These commands are used for device-related operations

#### Subcommands

##### list
* Usage:
`abxr-cli devices list`
* Description: List all devices


##### details
* Usage:
`abxr-cli devices details device_id`
* Positional Argument:
    * `device_id`: The unique identifier for the device.
* Description: Get detailed information about a device.


##### launch
* Usage:
`abxr-cli devices launch device_id --app_id=app_id`
* Positional Argument:
    * `device_id`: The unique identifier for the device.
* Required Options:
    * --app_id: The unique identifier of the application you want to launch
* Description: Launch an application immediately on a device.


##### reboot
* Usage:
`abxr-cli devices reboot device_id`
* Positional Argument:
    * `device_id`: The unique identifier for the device.
* Description: Reboot a device immediately.



## CLI Usage Examples

These examples assume you have set the `ABXR_API_TOKEN` in your environment. 

### Listing all apps

`abxr-cli apps list`

### Getting details of a specific app

`abxr-cli apps details 123e4567-e89b-12d3-a456-426614174000`

### Listing versions of an app

`abxr-cli apps versions 123e4567-e89b-12d3-a456-426614174000`

### Uploading a new version of an app

Basic upload:

`abxr-cli apps upload 123e4567-e89b-12d3-a456-426614174000 /path/to/app.apk --version 1.2.3 --notes "Bug fixes and performance improvements"`

Upload to an existing release channel:

`abxr-cli apps upload 123e4567-e89b-12d3-a456-426614174000 /path/to/app.apk --release-channel-id 9451f229-1833-4327-a708-e8a2a5c8d377`

Upload and create a new release channel:

`abxr-cli apps upload 123e4567-e89b-12d3-a456-426614174000 /path/to/app.apk --new-release-channel-title "Beta Channel"`

### Sharing an app with an organization

`abxr-cli apps share 123e4567-e89b-12d3-a456-426614174000 --release_channel_id 6789 --organization_slug myorg`

### Listing all files

`abxr-cli files list`

### Uploading an app bundle with files

Upload an APK and associated files from a folder:

`abxr-cli app_bundles upload 123e4567-e89b-12d3-a456-426614174000 /path/to/app.apk /path/to/bundle-folder`

With version number and release notes:

`abxr-cli app_bundles upload 123e4567-e89b-12d3-a456-426614174000 /path/to/app.apk /path/to/bundle-folder --version-number "1.0.0" --notes "Initial production release"`

With a custom device path (files will be placed under /sdcard/myapp/config/):

`abxr-cli app_bundles upload 123e4567-e89b-12d3-a456-426614174000 /path/to/app.apk /path/to/bundle-folder --device-path myapp/config`

Upload to an existing release channel:

`abxr-cli app_bundles upload 123e4567-e89b-12d3-a456-426614174000 /path/to/app.apk /path/to/bundle-folder --release-channel-id 9451f229-1833-4327-a708-e8a2a5c8d377`

Upload and create a new release channel:

`abxr-cli app_bundles upload 123e4567-e89b-12d3-a456-426614174000 /path/to/app.apk /path/to/bundle-folder --new-release-channel-title "Production Channel"`

### Listing app bundles

List all bundles for an app:

`abxr-cli app_bundles list 123e4567-e89b-12d3-a456-426614174000`

List only pending bundles:

`abxr-cli app_bundles list 123e4567-e89b-12d3-a456-426614174000 --status pending`

### Getting app bundle details

`abxr-cli app_bundles details 789e1234-e89b-12d3-a456-426614174000`

### Resuming a failed bundle upload

If an upload fails or is interrupted, you can resume it:

`abxr-cli app_bundles resume 789e1234-e89b-12d3-a456-426614174000 /path/to/app.apk /path/to/bundle-folder`

If the original upload used a custom device path, you must provide it when resuming:

`abxr-cli app_bundles resume 789e1234-e89b-12d3-a456-426614174000 /path/to/app.apk /path/to/bundle-folder --device-path myapp/config`

### Creating a bundle from an existing build

If you already have an uploaded build and want to create a bundle with files without re-uploading the APK:

`abxr-cli app_bundles create_from_build abc12345-e89b-12d3-a456-426614174000 /path/to/bundle-folder 123e4567-e89b-12d3-a456-426614174000`

With a custom device path:

`abxr-cli app_bundles create_from_build abc12345-e89b-12d3-a456-426614174000 /path/to/bundle-folder 123e4567-e89b-12d3-a456-426614174000 --device-path myapp/data`

With a release channel:

`abxr-cli app_bundles create_from_build abc12345-e89b-12d3-a456-426614174000 /path/to/bundle-folder 123e4567-e89b-12d3-a456-426614174000 --release-channel-id 9451f229-1833-4327-a708-e8a2a5c8d377`

Create multiple bundles from the same build with different file sets:

```bash
# First bundle with config files
abxr-cli app_bundles create_from_build abc12345-e89b-12d3-a456-426614174000 /path/to/config-files 123e4567-e89b-12d3-a456-426614174000

# Second bundle with media files
abxr-cli app_bundles create_from_build abc12345-e89b-12d3-a456-426614174000 /path/to/media-files 123e4567-e89b-12d3-a456-426614174000
```

### Updating an app bundle's label

Set a custom label for a bundle:

`abxr-cli app_bundles update_label 789e1234-e89b-12d3-a456-426614174000 --label "Production Release v2.0"`

Remove a label from a bundle:

`abxr-cli app_bundles update_label 789e1234-e89b-12d3-a456-426614174000 --clear`


## Error Handling

* If the API token is missing (not provided via --token or environment variables), the tool will print:

`API Token is required. Please set the ABXR_API_TOKEN environment variable or use the --token command line param`
