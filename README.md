## Introduction

s3Repo is a [Repo Plugin](https://github.com/munki/munki/wiki/Repo-Plugins) for [Munki 3](https://github.com/munki/munki/wiki/Munki-3-Information). This plugin allows administrators to securely interact with their munki repo hosted in a S3 compatible bucket.

s3Repo uses the [boto3](https://github.com/boto/boto3) python library.


## Getting Started

Before you can configure and use the s3Repo plugin you must have an S3 compatible backend, a bucket on the backend, and an account that has read/write permissions to the bucket. It is recommended, though not required, to have a separate bucket for your munki repo. [Amazon S3](https://aws.amazon.com/s3/) is the most popular S3 solution however others exist such as [Minio](https://www.minio.io/); which allows you to stand up your own S3 backend.

The s3Repo plugin can create the necessary subdirectories (catalogs, icons, manifests, pkgs, pkginfo) however by design will **not** attempt to create buckets.

### Setup

1. Install the boto3 python library:
    ```bash
    $ pip install boto3 --user
    ```
1. Download this repo plugin:
    ```bash
    $ git clone https://github.com/clburlison/Munki-s3Repo-Plugin.git
    $ cd Munki-s3Repo-Plugin
    $ sudo cp s3Repo.py /usr/local/munki/munkilib/munkirepo/
    ```
1. Make changes to the 'prefs' dictionary inside the `prefSetter.py` file.
  * Required values: `aws_access_key_id`, `aws_secret_access_key`, `bucket`, & `region`.
  * All values inside the 'ExtraArgs' dictionary are optional and can be omitted. For additional details on ExtraArgs please see [ALLOWED_UPLOAD_ARGS](http://boto3.readthedocs.io/en/latest/reference/customizations/s3.html#boto3.s3.transfer.S3Transfer.ALLOWED_UPLOAD_ARGS).
  * If using [Minio](https://www.minio.io/) or another S3 service you **must** set the `endpoint_url` to the desired url inside of your 'prefs'.
1. Run the `prefSetter.py` script to apply settings:
    ```bash
    $ ./prefSetter.py
    ```
1. Configure munkiimport:  
    _Note:_ you can set the Repo URL to anything you wish this plugin does not use that key. It will show up on `makecatalogs` runs so it is recommend to be S3 descriptive.

    ```bash
    $ munkiimport --configure

    Repo URL (example: afp://munki.example.com/repo): S3 Backend
    pkginfo extension (Example: .plist): .plist
    pkginfo editor (examples: /usr/bin/vi or TextMate.app; leave empty to not open an editor after import): Atom.app
    Default catalog to use (example: testing): testing
    Repo access plugin (defaults to FileRepo): s3Repo
    ```


## Implementation Notes
* `makecatalogs` works with the s3Repo plugin but is slow due to all the web calls needed to get every icon and pkginfo item.
* `iconimporter` has to download dmgs/pkgs from the repo in order to process them for possible icons. It's recommended that you avoid using it against the entire repo at this time.
* So that the s3Repo plugin can add customizations it does **not** read or respect any values inside of `~/.aws` this is a change from initialize design and standard boto3 usage. This allows s3Repo plugin preferences to be written with a macOS configuration profile if desired.
