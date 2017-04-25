#!/usr/bin/python
"""
Helper script to set preferences for s3Repo plugin.

Sorry I wanted nested dictonaries. Deal with it. This allows you to have
multiple 'profiles' for usage. Change the `profile_name` value and run this
script to create or update a profile. To switch to that profile use:

    export S3REPO_PROFILE='NEW_VALUE_HERE'     (sh/bash/zsh)
    set -x S3REPO_PROFILE 'NEW_VALUE_HERE'     (fish)

I am making the assumption that you wish to store your preferences under
~/Library/Preferences/com.clburlison.munki.s3Repo.

You will _need_ to make modifications to the `prefs` dictonary.
"""

from Foundation import CFPreferencesSetMultiple, \
                       kCFPreferencesAnyHost, \
                       kCFPreferencesCurrentUser


bundle_id = 'com.clburlison.munki.s3Repo'
profile_name = 'default'

prefs = {
            profile_name: {
                'aws_access_key_id': '1234',
                'aws_secret_access_key': 'asdf',
                'bucket': 'clburlison-munkirepo',
                'region': 'us-east-1',
                'ExtraArgs': {
                    'ACL': 'public-read',
                    'StorageClass': 'REDUCED_REDUNDANCY',
                    'Metadata': {
                        'Cache-Control': '86400',
                    },
                },
            }
         }

CFPreferencesSetMultiple(
    prefs,                      # 1. our dictionary of keys/values to set
    [],                         # 2. a list of keys to _remove_
    bundle_id,                  # 3. the domain
    kCFPreferencesCurrentUser,  # 4. current- or any-user (ie. ~/L/P or /L/P)
    kCFPreferencesAnyHost       # 5. current- or any-host (ie. ByHost or not)
)
