# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from celery.decorators import periodic_task

from core.utils.services import request_github_issues

ISSUE_UPDATE_PERIOD = 15 # in minutes


class Region(models.Model):
    """Used to store data for different regions."""
    region_name = models.CharField(max_length=100, unique=True)
    region_image = models.URLField(blank=True)

    class Meta:
        ordering = ('region_name',) # Ascending order according to region name.

    def __str__(self):
        return '%s' % (self.region_name)


class RegionAdmin(AbstractUser):
    regions = models.ManyToManyField(Region)


class UserRepo(models.Model):
    """
    UserRepo model is used to store the username and repo-name
    for a repository.
    """
    user = models.CharField(max_length=100)
    repo = models.CharField(max_length=100)
    author = models.ForeignKey(RegionAdmin)
    regions = models.ManyToManyField(Region)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created',) # Ascending order according to date created.
        unique_together = ("user", "repo", "author") # Avoid repo duplicates.

    def __str__(self):
        return '/%s/%s' % (self.user, self.repo)


class IssueLabel(models.Model):
    """
    Label model for storing labels of an issue.
    """
    label_id = models.IntegerField(primary_key=True)
    label_url = models.URLField()
    label_name = models.CharField(max_length=100)
    label_color = models.CharField(max_length=6)

    class Meta:
        ordering = ('label_name',) # Ascending order according to label_name.


class Issue(models.Model):
    """
    Issue model is used to store github issues.
    """
    # Setting choices for experience needed to solve an issue.
    EASYFIX = 'easyfix'
    MODERATE = 'moderate'
    SENIOR = 'senior'
    EXPERIENCE_NEEDED_CHOICES = (
        (EASYFIX, 'easyfix'),
        (MODERATE, 'moderate'),
        (SENIOR, 'senior'),
    )
    # Model attributes start from here.
    issue_id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)
    experience_needed = models.CharField(
        max_length=10,
        choices=EXPERIENCE_NEEDED_CHOICES,
        default=MODERATE,
    )
    expected_time = models.CharField(max_length=100)
    language = models.CharField(max_length=100)
    tech_stack = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    issue_number = models.IntegerField()
    issue_labels = models.ManyToManyField(IssueLabel, blank=True)
    issue_url = models.URLField()
    issue_body = models.TextField()
    regions = models.ManyToManyField(Region)
    
    class Meta:
        ordering = ('updated_at',) # Ascending order according to updated_at.


class LanguageKnowledgeBase(models.Model):
    """
    IssueKnowledgeBase model is used as a knowledge base for `languages`.
    """
    language = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return '%s' % (self.language)


class TechStackKnowledgeBase(models.Model):
    """
    TechStackKnowledgeBase model is used as a knowledge base for `tech_stack`.
    """
    tech_stack = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return '%s' % (self.tech_stack)


class ExperienceNeededKnowledgeBase(models.Model):
    """
    ExperienceNeededKnowledgeBase model is used as a knowledge base for `experience_needed`.
    """
    experience_needed = models.CharField(max_length=100, unique=True)
    correct_experience_needed_value = models.CharField(max_length=100)

    def __str__(self):
        return '%s - %s' % (self.experience_needed, self.correct_experience_needed_value)


# class ExpectedTimeKnowledgeBase(models.Model):
#     """
#     ExpectedTimeKnowledgeBase model is used as a knowledge base for `expected_time`.
#     """
#     expected_time = models.CharField(max_length=100)


@periodic_task(run_every=timedelta(minutes=ISSUE_UPDATE_PERIOD), name="periodic_issues_updater")
def periodic_issues_updater():
    """
    Update `Issue` model in the database in every
    `ISSUE_UPDATE_PERIOD` minutes.
    """
    list_of_repos = UserRepo.objects.values('id', 'user', 'repo',)
    for repo in list_of_repos:
        region_queryset = retrive_regions_for_a_user(repo['id'])
        issue_list = request_github_issues(repo['user'], repo['repo'])
        if issue_list['error']:
            print "Error" + str(issue_list['data'])
        else:
            for issue in issue_list['data']:
                validate_and_store_issue(issue, region_queryset)

def retrive_regions_for_a_user(user_repo_id):
    """Fetches all the regions related to a user."""
    region_queryset = Region.objects.filter(userrepo=user_repo_id)
    return region_queryset

def validate_and_store_issue(issue, region_queryset):
    """
    Validate issue:- if valid - store it into database,
    else - Do not store in database
    """
    if is_issue_state_open(issue):
        if is_issue_valid(issue):
            store_issue_in_db(issue, region_queryset)

def is_issue_state_open(issue):
    """
    Returns true if issue state is open else
    return false and delete the issue from database.
    """
    if issue['state'] == 'open':
        return True
    else:
        delete_closed_issues(issue) # Delete closed issues from db.
        return False

def is_issue_valid(issue):
    """
    Checks if issue is valid for system or not.
    Return True if valid else return false.
    """
    parsed = parse_issue_by_label(issue['labels'])
    if len(parsed) == 4:
        return True # issue is valid
    else:
        print 'Issue with id ' + str(issue['id']) + ' is not valid for our system.'
        return False # issue is not valid

def store_issue_in_db(issue, region_queryset):
    """Stores issue in db"""
    parsed_labels = parse_issue_by_label(issue['labels'])
    issue_instance = Issue(issue_id=issue['id'], title=issue['title'],
                           experience_needed=parsed_labels['experience_needed'], expected_time=parsed_labels['expected_time'],
                           language=parsed_labels['language'], tech_stack=parsed_labels['tech_stack'],
                           created_at=issue['created_at'], updated_at=issue['updated_at'],
                           issue_number=issue['number'], issue_url=issue['html_url'],
                           issue_body=issue['body'])
    issue_instance.save()
    for label in issue['labels']:
        label_instance = IssueLabel(label_id=label['id'], label_name=label['name'],
                                    label_url=label['url'], label_color=label['color'])
        label_instance.save()
        issue_instance.issue_labels.add(label_instance)
    issue_instance.regions.add(*region_queryset)

def delete_closed_issues(issue):
    """Delete issues that are closed on GitHub but present in our db"""
    try:
        issue_instance = Issue.objects.get(issue_id=issue['id'])
        issue_instance.delete()
    except Exception:
        print 'Closed issue with id ' + str(issue['id']) + ' is not present is database.'

def parse_issue_by_label(labels_list):
    """
    Parse issue labels and return `experience_needed`, `language`,
    `expected_time` and `technology_stack`.
    """
    parsed_data = {'expected_time': '20 days'}
    for label in labels_list:
        knowledgeClass, label_name = classify_label(label['name'])
        if knowledgeClass:
            parsed_data[knowledgeClass] = label_name

    return parsed_data

def classify_label(label):
    """Classify a label to a particular knowledge class."""
    label = label.strip().lower()

    experience_needed = 'experience_needed'
    language = 'language'
    tech_stack = 'tech_stack'
    correct_experience_needed_value = 'correct_experience_needed_value'

    experience_knowledge = ExperienceNeededKnowledgeBase.objects.values(experience_needed, correct_experience_needed_value)
    language_knowledge = LanguageKnowledgeBase.objects.values(language)
    tech_stack_knowledge = TechStackKnowledgeBase.objects.values(tech_stack)

    experience_knowledge_list = {}
    for exp in experience_knowledge:
        x = exp['experience_needed'].strip().lower()
        experience_knowledge_list[x] = exp['correct_experience_needed_value']

    language_knowledge_list = [i[language].strip().lower() for i in language_knowledge]
    tech_stack_knowledge_list = [i[tech_stack].strip().lower() for i in tech_stack_knowledge]

    if label in experience_knowledge_list:
        return experience_needed, experience_knowledge_list[label]
    elif label in language_knowledge_list:
        return language, label
    elif label in tech_stack_knowledge_list:
        return tech_stack, label
    else:
        return False, label

def find_between(string, first, last):
    """
    Return string between two substrings `first` and `last`.
    """
    try:
        start = string.index(first) + len(first)
        end = string.index(last, start)
        return string[start:end].replace(': ', '')
    except ValueError:
        return ""
