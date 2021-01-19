#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, urllib, urllib2, base64, re

class HTTPConnector(object):
    def __init__(self, debug):
        self.debug = debug

    def sendRequest(self, url, method=None, data=None, headers={}, timeout=None):
        request = urllib2.Request(url, headers=headers)
        if method:
            request.get_method = lambda: method
            
        sender = None
        if self.debug:
            handler = urllib2.HTTPSHandler(debuglevel=1)
            sender = urllib2.build_opener(handler).open
        else:
            sender = urllib2.urlopen
        
        response = sender(request, data=data, timeout=timeout)
        return json.loads(response.read().decode('utf-8'))

class GitlabConnector(HTTPConnector):
    def __init__(self, baseURL, token, debug=False):
        super(GitlabConnector, self).__init__(debug)
        self.baseURL = baseURL
        self.token = token
        
    perPageMax = 100
        
    # https://docs.gitlab.com/ee/api/README.html#encoding-api-parameters-of-array-and-hash-types
    def __urlencode(self, parameters):
        components = []
        for key in parameters:
            value = parameters[key]
            if type(value) is list:
                for element in value:
                    components.append('%s[]=%s' % (urllib.quote_plus(key), urllib.quote_plus(element)))
            elif type(value) is bool:
                components.append('%s=%s' % (urllib.quote_plus(key), 'true' if value else 'false'))
            else:
                components.append('%s=%s' % (urllib.quote_plus(key), urllib.quote_plus(str(value))))
        return '&'.join(components)
        
    def sendAPIRequest(self, path, method=None, data=None):
        headers = {'PRIVATE-TOKEN': self.token}
        url = self.baseURL + path
        return self.sendRequest(url, method=method, headers=headers, data=data)

    def paginating(self, function):
        page = 1
        while True:
            results = function(page)
            if not results:
                break
            for result in results:
                yield result
            page += 1

    def getProjectMergeRequests(self, id, attributes=None):
        path = '/projects/%s/merge_requests' % id
        if attributes:
            path += '?' + self.__urlencode(attributes)
        return self.sendAPIRequest(path)

    def updateProjectMergeRequest(self, id, mergeRequestIid, attributes):
        path = '/projects/%s/merge_requests/%s' % (id, mergeRequestIid)
        data = self.__urlencode(attributes)
        return self.sendAPIRequest(path, method='PUT', data=data)

    def createProjectLabel(self, id, attributes):
        path = '/projects/%s/labels' % id
        data = self.__urlencode(attributes)
        return self.sendAPIRequest(path, method='POST', data=data)

    def getProjectLabels(self, id, page=None, perPage=None):
        path = '/projects/%s/labels' % id
        parameters={}
        if page:
            parameters.update({'page': page})
        if page:
            parameters.update({'per_page': perPage})
        if len(parameters) > 0:
            path += '?' + self.__urlencode(parameters)
        return self.sendAPIRequest(path)
        
    def getProjectMember(self, id, query=None):
        path = '/projects/%s/members/all' % id
        if query:
            parameters = {'query': query}
            path += '?' + self.__urlencode(parameters)
        members = self.sendAPIRequest(path)
        if len(members) == 0:
            return None
        else:
            return members[0]

    def getProjectAwardEmojis(self, id, mergeRequestIid):
        path = '/projects/%s/merge_requests/%s/award_emoji' % (id, mergeRequestIid)
        return self.sendAPIRequest(path)

    def getProjectMergeRequestDiscussions(self, id, mergeRequestIid):
        path = '/projects/%s/merge_requests/%s/discussions' % (id, mergeRequestIid)
        return self.sendAPIRequest(path)
        
    # List repository commits
    # see https://docs.gitlab.com/ee/api/commits.html#list-repository-commits
    def getProjectCommits(self, id, refName=None):
        path = '/projects/%s/repository/commits' % id
        parameters={}
        if refName:
            parameters.update({'ref_name': refName})
        if len(parameters) > 0:
            path += '?' + self.__urlencode(parameters)
        return self.sendAPIRequest(path)
        
    def getProjectTags(self, id, search=None):
        path = '/projects/%s/repository/tags' % id
        parameters={}
        if search:
            parameters.update({'search': search})
        if len(parameters) > 0:
            path += '?' + self.__urlencode(parameters)
        return self.sendAPIRequest(path)
        
    def getProjectIssueKeys(self, id, refName):
        issueKeys = set([])
        commits = self.getProjectCommits(id, refName)
        for commit in commits:
            matches = re.findall('TDZ-(\d+)', commit['message'], flags=re.I)
            keys = map(lambda x: 'TDZ-' + x, matches)
            issueKeys.update(keys)
        return issueKeys

class JIRAConnector(HTTPConnector):
    def __init__(self, url, username, password, debug=False):
        super(JIRAConnector, self).__init__(debug)
        self.url = url
        self.username = username
        self.password = password
        
    def sendAPIRequest(self, path, timeout=None):
        base64string = base64.encodestring('%s:%s' % (self.username, self.password))[:-1]
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Basic %s' % base64string
        }
        return self.sendRequest('%s/rest/api/2%s' % (self.url, path), headers=headers, timeout=timeout)

    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/#api-rest-api-2-issue-issueIdOrKey-get
    def getIssue(self, issuesIdOrKey, fields=None, fieldsByKeys=None, expand=None, properties=None, updateHistory=None, timeout=120):
        path = '/issue/%s' % issuesIdOrKey
        parameters = {}
        if fields:
            parameters.update({'fields': fields})
        if len(parameters) > 0:
            path += '?' + urllib.urlencode(parameters)
        return self.sendAPIRequest(path, timeout=timeout)

    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/#api-rest-api-2-search-get
    def search(self, jql, fields=None, maxResults=None, validateQuery=None):
        path = '/search'
        parameters = {}
        if jql:
            parameters.update({'jql': jql})
        if fields:
            parameters.update({'fields': fields})
        if maxResults:
            parameters.update({'maxResults': maxResults})
        if validateQuery:
            parameters.update({'validateQuery': validateQuery})
        if len(parameters) > 0:
            path += '?' + urllib.urlencode(parameters)
        return self.sendAPIRequest(path)

    def paginating(self, values, function, pageSize=50):
        slice = []
        results = []
            
        while len(values) > 0:
            # collect values for next page
            if len(slice) < pageSize:
                slice.append(values.pop())

            # fetch page
            if len(values) == 0 or len(slice) == pageSize:
                results += function(slice, pageSize)
                slice = []

        return results
        
    # Returns a user
    def user(self, username):
        path = '/user'
        parameters = {'username': username}
        path += '?' + urllib.urlencode(parameters)
        return self.sendAPIRequest(path)

class SlackConnector(HTTPConnector):
    def __init__(self, token, debug=False):
        super(SlackConnector, self).__init__(debug)
        self.url = 'https://slack.com/api'
        self.token = token
        self.pretty = debug

    def sendAPIRequest(self, path, method=None, parameters=None):
        url = self.url + path
        headers = {}
        queryParameters = None
        bodyParameters = None
        
        is_get = method is None or method.lower() == 'get'
        if is_get:
            queryParameters = {'token': self.token}
            if self.pretty:
                queryParameters.update({'pretty': '1'})
            if parameters:
                queryParameters.update(parameters)
        else:
            headers = {
                'Authorization': 'Bearer ' + self.token,
                'Content-type': 'application/json'
            }
            if parameters:
                bodyParameters = {'pretty': '1'}
                bodyParameters.update(parameters)
        
        if queryParameters:
            url += '?' + urllib.urlencode(queryParameters)

        data = None
        if bodyParameters:
            data = json.dumps(parameters, ensure_ascii=False)
            
        return self.sendRequest(url, method = method, data = data, headers = headers)

    def postMessage(self, channel, text, username=None):
        parameters = {'channel': channel, 'text': text}
        if username:
            parameters.update({'username': username})

        return self.sendAPIRequest('/chat.postMessage', method = 'POST', parameters = parameters)

    def getUserInfo(self, user):
        return self.sendAPIRequest('/users.info', parameters = {'user': user})

    def getDndInfo(self, user):
        return self.sendAPIRequest('/dnd.info', parameters = {'user': user})
        
    def getUsersList(self):
        return  self.sendAPIRequest('/users.list')
