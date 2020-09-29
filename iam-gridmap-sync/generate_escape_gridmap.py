import os
import requests
import json
from configparser import ConfigParser

import logging
logging.basicConfig(level=logging.DEBUG)

CONFIG_PATH = "./iam-gridmap.conf"


class IAM_Gridmap_Generator():

    TOKEN_URL = "/token"
    GET_USERS_URL = "/scim/Users"

    def __init__(self, config_path):
        self.config_path = config_path
        self.configure()

    def generate(self):
        access_token = self.get_token()
        users = self.get_list_of_users(access_token)
        cert = self.extract_certificates(users)
        self.write_gridmap(cert, self.default_role, self.gridmap_path)

    def configure(self):
        self.iam_server = None
        self.default_role = 'ops001'
        self.client_id = None
        self.client_secret = None
        self.token_server = None
        self.gridmap_path = None

        config = ConfigParser()
        files_read = config.read(self.config_path)
        if len(files_read) > 0:
            self.iam_server = config.get('IAM', 'iam-server')
            self.default_role = config.get('IAM', 'default-role')
            self.client_id = config.get('IAM', 'client-id')
            self.gridmap_path = config.get('IAM', 'output_gridmap_path')

            if config.has_option('IAM', 'client-secret'):
                self.client_secret = config.get('IAM', 'client-secret')
            else:
                client_secret_path = config.get('IAM', 'client-secret-path')
                with open(client_secret_path, 'r') as client_secret_file:
                    self.client_secret = client_secret_file.read().rstrip()

            if config.has_option('IAM', 'token-server'):
                self.token_server = config.get('IAM', 'token-server')
            else:
                self.token_server = self.iam_server

        # Overwrite config with ENV variables
        self.iam_server = os.getenv('IAM_SERVER', self.iam_server)
        self.client_id = os.getenv('IAM_CLIENT_ID', self.client_id)
        self.client_secret = os.getenv('IAM_CLIENT_SECRET', self.client_secret)
        self.token_server = os.getenv('IAM_TOKEN_SERVER', self.token_server)
        self.gridmap_path = os.getenv('IAM_GRIDMAP_PATH', self.gridmap_path)
        if self.token_server is None:
            self.token_server = self.iam_server

        # Validate all required settings are set or throw exception
        # TODO

    def get_token(self):
        """
        Authenticates with the iam server and returns the access token.
        """
        request_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "username": "not_needed",
            "password": "not_needed",
            "scope": "scim:read"
        }
        r = requests.post(self.token_server + self.TOKEN_URL, data=request_data)
        responce = json.loads(r.text)

        if 'access_token' not in responce:
            raise BaseException("Authentication Failed")

        return responce['access_token']

    def get_list_of_users(self, access_token):
        """
        Queries the server for all users belonging to the VO.
        """
        header = {"Authorization": "Bearer %s" % access_token}
        r = requests.get("%s/scim/Users" % self.iam_server, headers=header)
        # TODO: Handle exceptions, error codes
        return json.loads(r.text)

    def make_gridmap_compatible(self, certificate):
        """
        Take a certificate and make it compatible with the gridmap format.
        Basically reverse it and replace ',' with '/'
        """
        certificate = certificate.split(',')
        certificate.reverse()
        certificate = '/'.join(certificate)
        certificate = '/' + certificate
        return certificate

    def extract_certificates(self, users):
        grid_certificates = []
        for user in users['Resources']:
            if 'urn:indigo-dc:scim:schemas:IndigoUser' in user:
                indigo_user = user['urn:indigo-dc:scim:schemas:IndigoUser']
                if 'certificates' in indigo_user:
                    for certificate in indigo_user['certificates']:
                        if 'subjectDn' in certificate:
                            grid_certificate = self.make_gridmap_compatible(certificate['subjectDn'])
                            grid_certificates.append(grid_certificate)
        return grid_certificates

    def write_gridmap(self, certificates, role, path):
        with open(path, 'w') as output:
            for certificate in certificates:
                line = '"%s" %s\n' % (certificate, role)
                output.write(line)


if __name__ == '__main__':
    logging.info("* Sync to IAM (Gridmap) * Initializing IAM-Gridmap synchronization script.")
    grid_test = IAM_Gridmap_Generator(CONFIG_PATH)
    grid_test.generate()

    logging.info("* Sync to IAM (Gridmap) * Successfully completed.")