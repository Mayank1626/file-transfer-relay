import os
import boto3
from flask import request
from app.storage.base import StorageEngine

class S3StorageEngine(StorageEngine):
    """Storage Engine interfacing with AWS S3 or MinIO object storage."""
    
    def __init__(self):
        self.endpoint_url = None
        self.access_key = None
        self.secret_key = None
        self.bucket = None
        self.signature_version = None
        self._s3_client = None
        
    def init_app(self, app):
        self.endpoint_url = app.config['S3_ENDPOINT']
        self.access_key = app.config['S3_ACCESS_KEY']
        self.secret_key = app.config['S3_SECRET_KEY']
        self.bucket = app.config['S3_BUCKET']
        self.signature_version = app.config['S3_SIGNATURE_VERSION']
        
        # Instantiate primary connection
        self._s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=boto3.session.Config(signature_version=self.signature_version)
        )
        
        # Ensure bucket exists
        try:
            self._s3_client.create_bucket(Bucket=self.bucket)
        except Exception:
            pass
            
        # Ensure bucket 24-hour lifecycle is active
        try:
            self._s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket,
                LifecycleConfiguration={
                    'Rules': [
                        {
                            'ID': 'AutoTrashOldFiles',
                            'Status': 'Enabled',
                            'Filter': {'Prefix': ''},
                            'Expiration': {'Days': 1},
                            'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 1}
                        }
                    ]
                }
            )
        except Exception as e:
            app.logger.warning(f"S3/MinIO bucket lifecycle config warning: {e}")
            
    def _get_signing_client(self):
        """Creates a dynamically-routed boto3 client for browser presigned URL usage."""
        try:
            req_host = request.host.split(':')[0]
            protocol = request.headers.get('X-Forwarded-Proto', 'http')
            signing_url = f"{protocol}://{req_host}"
        except Exception:
            signing_url = self.endpoint_url
            
        return boto3.client(
            's3',
            endpoint_url=signing_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=boto3.session.Config(
                signature_version=self.signature_version,
                s3={'addressing_style': 'path'}  # Force Path for Nginx bucket matching relay
            )
        )
        
    def _get_key(self, pin, filename):
        return f"{pin}_{filename}"
        
    def generate_upload_url(self, pin, filename, content_type):
        key = self._get_key(pin, filename)
        signing_client = self._get_signing_client()
        url = signing_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket,
                'Key': key,
                'ContentType': content_type
            },
            ExpiresIn=900
        )
        return url
        
    def generate_download_url(self, pin, filename):
        key = self._get_key(pin, filename)
        signing_client = self._get_signing_client()
        url = signing_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket,
                'Key': key,
                'ResponseContentDisposition': f'attachment; filename="{filename}"'
            },
            ExpiresIn=3600  # 1 hour
        )
        return url
        
    def upload_file(self, pin, file):
        key = self._get_key(pin, file.filename)
        self._s3_client.upload_fileobj(file.stream, self.bucket, key)
        return key
        
    def download_file(self, pin, filename):
        key = self._get_key(pin, filename)
        try:
            obj = self._s3_client.get_object(Bucket=self.bucket, Key=key)
            return obj['Body'], False  # Returns raw file stream, download attachment is False since we return raw stream
        except Exception:
            return None, False
            
    def delete_file(self, pin, filename):
        key = self._get_key(pin, filename)
        try:
            self._s3_client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            pass
