#!/usr/bin/env python3
"""
Upload a Lambda layer to AWS.

This script uploads a zip file as an AWS Lambda layer, configured for Python 3.12-3.14
on ARM64 architecture.

Setup:
    1. Install required dependencies:
       pip install boto3

    2. Configure AWS credentials using one of:
       - AWS CLI: aws configure
       - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
       - AWS credentials file: ~/.aws/credentials

    3. Ensure you have permissions for lambda:PublishLayerVersion

Usage:
    # Upload with defaults (us-east-1 region)
    ./upload_layer.py my-layer.zip --layer-name my-layer-name

    # Specify custom region
    ./upload_layer.py my-layer.zip --layer-name my-layer --region ap-southeast-1

    # With description
    ./upload_layer.py layer.zip --layer-name my-layer --description "My custom Lambda layer"

Arguments:
    zip_file            Path to the zip file (required)
    --layer-name, -n    Name for the Lambda layer (required)
    --region, -r        AWS region (default: us-east-1)
    --description, -d   Description for the layer
"""
import boto3
import argparse
import sys
from pathlib import Path


def upload_lambda_layer(zip_file_path, layer_name, region, description=None):
    """
    Upload a zip file as a Lambda layer.

    Args:
        zip_file_path: Path to the zip file
        layer_name: Name for the Lambda layer
        region: AWS region
        description: Optional description for the layer

    Returns:
        Response from the publish_layer_version API call
    """
    # Create Lambda client for the specified region
    lambda_client = boto3.client('lambda', region_name=region)

    # Read the zip file
    zip_path = Path(zip_file_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_file_path}")

    print(f"Reading zip file: {zip_path}")
    print(f"File size: {zip_path.stat().st_size / (1024*1024):.2f} MB")

    with open(zip_path, 'rb') as f:
        zip_content = f.read()

    # Prepare the publish parameters
    publish_params = {
        'LayerName': layer_name,
        'Content': {
            'ZipFile': zip_content
        },
        'CompatibleRuntimes': ['python3.14', 'python3.13', 'python3.12'],
        'CompatibleArchitectures': ['arm64']
    }

    if description:
        publish_params['Description'] = description
    else:
        publish_params['Description'] = f"Lambda layer for {layer_name}"

    # Publish the layer
    print(f"\nUploading layer '{layer_name}' to region '{region}'...")
    response = lambda_client.publish_layer_version(**publish_params)

    # Print success information
    print("\n✓ Layer uploaded successfully!")
    print(f"Layer ARN: {response['LayerArn']}")
    print(f"Version: {response['Version']}")
    print(f"Version ARN: {response['LayerVersionArn']}")

    return response


def main():
    parser = argparse.ArgumentParser(
        description='Upload a zip file as a Lambda layer'
    )
    parser.add_argument(
        'zip_file',
        help='Path to the zip file'
    )
    parser.add_argument(
        '--layer-name',
        '-n',
        required=True,
        help='Name for the Lambda layer'
    )
    parser.add_argument(
        '--region',
        '-r',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--description',
        '-d',
        help='Description for the layer'
    )

    args = parser.parse_args()

    try:
        upload_lambda_layer(
            zip_file_path=args.zip_file,
            layer_name=args.layer_name,
            region=args.region,
            description=args.description
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
