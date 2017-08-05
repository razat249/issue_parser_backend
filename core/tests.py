"""
This file contains all the tests related to `issue parser core` app.
"""

# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from requests.exceptions import ConnectionError

from .models import (UserRepo, validate_and_store_issue, Issue, delete_closed_issues, 
                     is_issue_valid, is_issue_state_open, periodic_issues_updater, Region, RegionAdmin,
                     retrive_regions_for_a_user, ExperienceNeededKnowledgeBase, LanguageKnowledgeBase, TechStackKnowledgeBase,
                     classify_label, parse_issue_by_label)
from .utils.mock_api import api_response_issues
from .utils.services import request_github_issues

SAMPLE_VALID_ISSUE = api_response_issues[0]

class UserRepoModelTestCase(TestCase):
    """This class defines the test suite for the `UserRepo` model."""

    def setUp(self):
        """Define the test client and other test variables."""
        self.user = 'razat249'
        self.repo = 'github-view'
        self.author = RegionAdmin.objects.create_user(
            username='jacob', password='top_secret'
        )
        self.user_repo = UserRepo(user=self.user, repo=self.repo, author=self.author)

    def test_user_repo_model_can_create_a_userrepo(self):
        """Test the `UserRepo` model can create a `user_repo`."""
        old_count = UserRepo.objects.count()
        self.user_repo.save()
        new_count = UserRepo.objects.count()
        self.assertNotEqual(old_count, new_count)

    def test_user_repo_model_can_delete_a_userrepo(self):
        """Test the `UserRepo` model can delete a `user_repo`."""
        old_count = UserRepo.objects.count()
        self.user_repo.save()
        self.user_repo.delete()
        new_count = UserRepo.objects.count()
        self.assertEqual(old_count, new_count)

class RegionModelTestCase(TestCase):
    """This class defines the test suite for the `Region` model."""
    
    def setUp(self):
        """Define the test client and other test variables."""
        self.region_name = 'Mozilla India'
        self.region_image = 'https://example.com/image.jpg'
        self.region_instance = Region(region_name=self.region_name, region_image=self.region_image)

    def test_region_model_can_create_region(self):
        """Tests `Region` model can create Regions"""
        old_count = Region.objects.count()
        self.region_instance.save()
        new_count = Region.objects.count()
        self.assertNotEqual(old_count, new_count)

    def test_region_model_can_delete_region(self):
        """Tests `Region` model can delete Regions"""
        old_count = Region.objects.count()
        self.region_instance.save()
        self.region_instance.delete()
        new_count = Region.objects.count()
        self.assertEqual(old_count, new_count)

class IssueModelAndFetcherTestCase(TestCase):
    """This class defines the test suite for the `issue fetcher` component."""

    def setUp(self):
        """Initial setup for running tests."""
        self.USER_ID = 1
        self.USER_REPO_ID = 1
        self.author = RegionAdmin.objects.create_user(
            id=self.USER_ID, username='jacob', password='top_secret'
        )
        self.region = Region(region_name="Mozilla India")
        self.region.save()
        self.user_repo = UserRepo(id=self.USER_REPO_ID, user='razat249', repo='github-view', author=self.author)
        self.user_repo.save()
        self.user_repo.regions.add(self.region)        
        self.region_queryset = Region.objects.filter(userrepo=self.USER_ID)

        instance1 = ExperienceNeededKnowledgeBase(experience_needed='easyfix',
                                                  correct_experience_needed_value='easy')
        instance1.save()
        instance2 = ExperienceNeededKnowledgeBase(experience_needed='moderate',
                                                  correct_experience_needed_value='moderate')
        instance2.save()
        instance3 = ExperienceNeededKnowledgeBase(experience_needed='senior',
                                                  correct_experience_needed_value='senior')
        instance3.save()

        instance4 = LanguageKnowledgeBase(language='python')
        instance4.save()
        instance5 = LanguageKnowledgeBase(language='javascript')
        instance5.save()

        instance6 = TechStackKnowledgeBase(tech_stack='django')
        instance6.save()
        instance7 = TechStackKnowledgeBase(tech_stack='react.js')
        instance7.save()

    def test_api_can_request_issues(self):
        """Test the request function"""
        payload = request_github_issues('razat249', 'github-view')
        if payload['error_type'] == ConnectionError:
            pass
        else:
            self.assertEqual(payload['error'], False)
            self.assertLess(payload['status_code'], 400)

    def test_api_request_can_handle_errors(self):
        """Test the request function can handle errors"""
        # wrong repo name to test error handling.
        payload = request_github_issues('razat249', 'wrong_repo')
        if payload['error_type'] == ConnectionError:
            pass
        else:
            self.assertEqual(payload['error'], True)
            self.assertGreaterEqual(payload['status_code'], 400)

    def test_correct_issue_parsing(self):
        """Test for correct parsing of issues"""
        issue = SAMPLE_VALID_ISSUE.copy()
        parsed = parse_issue_by_label(issue['labels'])
        self.assertEqual(4, len(parsed))

    def test_issue_valid_and_not_valid_cases(self):
        """Test for checking if issue is valid or not"""
        valid_issue = SAMPLE_VALID_ISSUE.copy()
        invalid_issue = valid_issue.copy()
        invalid_issue['labels'] = []
        self.assertTrue(is_issue_valid(valid_issue))
        self.assertFalse(is_issue_valid(invalid_issue))

    def test_issue_state_open_or_not(self):
        """Test for checking issue state"""
        open_issue = SAMPLE_VALID_ISSUE.copy()
        closed_issue = SAMPLE_VALID_ISSUE.copy()
        closed_issue['state'] = 'closed'
        self.assertTrue(is_issue_state_open(open_issue))
        self.assertFalse(is_issue_state_open(closed_issue))

    def test_validate_and_store_issue(self):
        """Test for validating and storing issues."""
        old_count = Issue.objects.count()
        validate_and_store_issue(SAMPLE_VALID_ISSUE, self.region_queryset)
        new_count = Issue.objects.count()
        self.assertLess(old_count, new_count)

    def test_api_can_delete_closed_issues_in_db(self):
        """Test for checking if issues are deleted when closed online but present in db"""
        issue = SAMPLE_VALID_ISSUE.copy()
        validate_and_store_issue(issue, self.region_queryset)
        issue['state'] = 'closed'
        old_count = Issue.objects.count()
        delete_closed_issues(issue)
        new_count = Issue.objects.count()
        self.assertLess(new_count, old_count)

    def test_retrive_regions_for_a_user(self):
        """Test function can retrive regions for a user."""
        regions = retrive_regions_for_a_user(self.USER_REPO_ID)
        self.assertEqual(regions[0], self.region_queryset[0])

    def test_label_can_be_categorized(self):
        "Test function can classify label to different knowledge classes."
        received_label1 = 'easyfix'
        output = 'experience_needed'
        classified_class = classify_label(received_label1)
        self.assertEqual(classified_class, output)

    def test_api_can_parse_issue_labels(self):
        """Test for parsing labels."""
        labels_list = SAMPLE_VALID_ISSUE['labels']

        expected_output = {
            'expected_time': '20 days',
            'experience_needed': 'moderate',
            'language': 'python',
            'tech_stack': 'django',
        }
        output = parse_issue_by_label(labels_list)
        self.assertEqual(output, expected_output)

class ViewTestCase(TestCase):
    """This class defines the test suite for the api views."""

    def setUp(self):
        """Define the test client and other test variables."""
        self.mock_regions = ["a", "n", "e", "b", "d", "c"]        
        self.client = APIClient()
        region_queryset = Region.objects.all()
        for issue in api_response_issues:
            validate_and_store_issue(issue, region_queryset)

    def test_api_can_get_region_list(self):
        """Test the api can get given region list."""
        response = self.client.get('/regionlist/', format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_can_get_region_list_ordered_by_name(self):
        """Test the api gives list of regions in accessending order."""
        for s in self.mock_regions:
            region_list = Region(region_name=s)
            region_list.save()
        response = self.client.get('/regionlist/', format="json")
        response_content = json.loads(response.content)
        sorted_mock_regions = sorted(self.mock_regions)
        for i in xrange(len(sorted_mock_regions)):
            self.assertEqual(sorted_mock_regions[i], response_content[i]['region_name'])

    def test_api_can_get_metadata(self):
        """Test the api can get given metadata."""
        response = self.client.get('/metadata/', format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_can_get_issues_list(self):
        """Test the api can get given issues list."""
        response = self.client.get('/issues/', format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_can_get_filtered_issues_list(self):
        """Test api can get filtered issues list."""
        path = '/issues/?language=python&tech_stack=django&experience_needed=moderate'
        response = self.client.get(path, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(api_response_issues), len(json.loads(response.content)))

    def test_api_can_sort_issues_correctly(self):
        """Test api can sort the issues list correctly."""
        issues_list = Issue.objects.values_list('experience_needed').order_by('experience_needed')
        response = self.client.get('/issues/?ordering=experience_needed', format="json")
        response_content = json.loads(response.content)
        for i in xrange(len(issues_list)):
            self.assertEqual(issues_list[i][0], response_content[i]['experience_needed'])
