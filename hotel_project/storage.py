from whitenoise.storage import CompressedManifestStaticFilesStorage

class MyStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False
