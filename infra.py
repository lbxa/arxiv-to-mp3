import pulumi
from pulumi_gcp import storage, projects
from pulumi import Config

config = Config()
bucket_name = config.require("bucketName") 

# Create the storage bucket
podcast_bucket = storage.Bucket(
    bucket_name,
    name=bucket_name,  
    location="AUSTRALIA-SOUTHEAST1",
    uniform_bucket_level_access=True,  
    website=storage.BucketWebsiteArgs(
        main_page_suffix="index.html",
        not_found_page="404.html",
    ),
    cors=[{
        "origins": ["https://lbxa.github.io"],
        "methods": [
            "GET",
            "HEAD",
            "PUT",
            "POST",
            "DELETE",
        ],
        "response_headers": ["*"],
        "max_age_seconds": 3600,
    }],
    versioning=storage.BucketVersioningArgs(
        enabled=True,
    ),
    lifecycle_rules=[storage.BucketLifecycleRuleArgs(
        action=storage.BucketLifecycleRuleActionArgs(
            type="Delete",
        ),
        condition=storage.BucketLifecycleRuleConditionArgs(
            age=365,  # Delete objects older than 365 days
        ),
    )],
)

# Grant public read access to the bucket
public_iam_binding = storage.BucketIAMBinding(
    f"{bucket_name}-public-read",
    bucket=podcast_bucket.name,
    role="roles/storage.objectViewer",
    members=["allUsers"],
)

# Export the bucket name and public URL
pulumi.export("bucket_name", podcast_bucket.name)
pulumi.export("bucket_url", pulumi.Output.concat("https://storage.googleapis.com/", podcast_bucket.name, "/"))
