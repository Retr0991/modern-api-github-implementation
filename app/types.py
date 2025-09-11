from __future__ import annotations

from typing import List, Optional, TypedDict


class UserMetadata(TypedDict, total=False):
    name: str
    node_id: str
    profile_url: str
    avatar_url: str
    bio: str
    type: str
    company: str
    location: str
    email: str
    blog: str
    twitter_username: str
    created_at: str
    followers: int
    following: int
    followers_url: str
    following_url: str
    public_repos: int
    public_gists: int


class RepoMetadata(TypedDict, total=False):
    name: Optional[str]
    description: Optional[str]
    language: Optional[str]
    star_count: int
    fork_count: int
    issue_count: int
    created_at: str
    updated_at: str
    url: str
    # Enriched by extract_keywords_activity
    auto_tags: List[str]


class SummaryStats(TypedDict):
    total_public_repos: int
    total_followers: int
    total_following: int
    total_public_gists: int


class RawData(TypedDict):
    user_data: UserMetadata
    repo_data: List[RepoMetadata]
