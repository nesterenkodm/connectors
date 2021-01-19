#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse, json
from connector import JIRAConnector

def main():
    parser = argparse.ArgumentParser(description='JIRA User Info')
    parser.add_argument('-d', '--debug', action='store_true', help='Prints url requests for debugging purposes')
    parser.add_argument('--jira_url', required=True, help='JIRA URL')
    parser.add_argument('--jira_username', required=True, help='JIRA username')
    parser.add_argument('--jira_password', required=True, help='JIRA password')
    args = parser.parse_args()

    jira = JIRAConnector(args.jira_url, args.jira_username, args.jira_password, args.debug)
    result = jira.user(jira.username)
    
    print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == '__main__':
    main()
