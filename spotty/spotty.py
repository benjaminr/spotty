# coding=utf-8
import praw
import re
import spotipy as sp
import requests
import time
import datetime
import click
import spotipy.util as util
import os

# Spotify Creds ###################################################
# Environment variables should be set for the following:
# SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
###################################################################

# Reddit Creds ####################################################
REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
###################################################################


class SubredditPlaylistBuilder:
    """
    Builds a Spotify playlist by scraping a given subreddit for "artist - track" pattern in submission titles.
    """
    def __init__(self,
                 spotify_username,
                 subreddit="listentothis"):

        self.spotify_username = spotify_username
        self.subreddit = subreddit

        # Build client sessions
        self.spotify = self._create_spotify_session()

        self.reddit = self._create_reddit_session()

        # Scrape tracks
        self.scraped_tracks = self.scrape_subreddit()

        # Add tracks
        self.playlist_name = None
        self.playlist_id = None
        self.add_tracks_to_playlist()

    def _create_spotify_session(self):
        """
        Uses environment vars for Client ID, Secret and Redirect URI to create a Spotify
        session.

        :return: Instance of Spotify Session.
        """
        scope = "playlist-modify-private"
        try:
            token = util.prompt_for_user_token(self.spotify_username, scope)

            if token:
                print("Successfully established Spotify session.")
                return sp.Spotify(auth=token)
            else:
                raise ValueError("No token")
        except Exception as e:
            raise e

    def _create_reddit_session(self):
        """
        Uses environment vars for Client ID and Secret to create a Reddit session.

        :return: Instance of Reddit Session.
        """

        try:
            return praw.Reddit(client_id=REDDIT_CLIENT_ID,
                               client_secret=REDDIT_CLIENT_SECRET,
                               user_agent='Spotty v0.1')
        except requests.HTTPError as e:
            if e.errno in [429, 500, 502, 503, 504]:
                print("Reddit is down (error %s), sleeping..." % e.errno)
                time.sleep(60)
                pass
            else:
                raise e
        except Exception as e:
            print("couldn't Reddit: %s" % str(e))

    def scrape_subreddit(self):
        """
        Method for scraping all potential tracks from a subreddit. Submission titles
        are validated using an "artist - title" regex in track_validator.
        """
        tracks = []

        def track_validator(submission):
            artist_regex = re.compile('(\w.+) \-\-?')
            title_regex = re.compile('\w.+ --? (\w.+) \[')

            try:
                if re.match(artist_regex, submission.title):
                    artist = re.match(artist_regex, submission.title).group(1)
                    if re.match(title_regex, submission.title):
                        title = re.match(title_regex, submission.title).group(1)
                        return artist, title
                return False
            except Exception as e:
                print(e)
                return False

        for submission in self.reddit.subreddit(self.subreddit).top('week'):
            try:
                tracks.append(track_validator(submission))
            except Exception as e:
                print(e)

        return tracks

    def add_tracks_to_playlist(self):
        """
        Checks scraped tracks from Reddit exist in Spotify, builds a playlist and adds tracks.
        """

        spotify_tracks = []

        try:
            for track in self.scraped_tracks:
                if track:
                    searchtrack = self.spotify.search(
                        '%s %s' %
                        (track[0], track[1]))

                    if searchtrack["tracks"]["items"]:
                        search_result_artist = searchtrack["tracks"]["items"][0]["artists"][0]["name"]
                        search_result_track = searchtrack["tracks"]["items"][0]["name"]

                        print(f"Reddit  : {track[0]} - {track[1]}")
                        print(f"Spotify : {search_result_artist} - {search_result_track}")
                        print("---------------------------------------")
                        spotify_tracks.append(searchtrack["tracks"]["items"][0]["id"])

            if spotify_tracks:
                # Create new playlist with subreddit as title
                user_id = self.spotify.me()["id"]
                self.playlist_name = self.subreddit + " - " + str(datetime.date.today())
                self.playlist_id = self.spotify.user_playlist_create(user_id, self.playlist_name, public=False)['id']

            self.spotify.user_playlist_add_tracks(self.spotify.me()['id'],
                                                  self.playlist_id,
                                                  spotify_tracks)

        except Exception as e:
            print(e)


if __name__ == "__main__":
    print('''


      ██████  ██▓███   ▒█████  ▄▄▄█████▓▄▄▄█████▓▓██   ██▓
    ▒██    ▒ ▓██░  ██▒▒██▒  ██▒▓  ██▒ ▓▒▓  ██▒ ▓▒ ▒██  ██▒
    ░ ▓██▄   ▓██░ ██▓▒▒██░  ██▒▒ ▓██░ ▒░▒ ▓██░ ▒░  ▒██ ██░
      ▒   ██▒▒██▄█▓▒ ▒▒██   ██░░ ▓██▓ ░ ░ ▓██▓ ░   ░ ▐██▓░
    ▒██████▒▒▒██▒ ░  ░░ ████▓▒░  ▒██▒ ░   ▒██▒ ░   ░ ██▒▓░
    ▒ ▒▓▒ ▒ ░▒▓▒░ ░  ░░ ▒░▒░▒░   ▒ ░░     ▒ ░░      ██▒▒▒
    ░ ░▒  ░ ░░▒ ░       ░ ▒ ▒░     ░        ░     ▓██ ░▒░
    ░  ░  ░  ░░       ░ ░ ░ ▒    ░        ░       ▒ ▒ ░░
          ░               ░ ░                     ░ ░
                                                  ░ ░


    Welcome to Spotty.

    Spotty is a script for scraping subreddits and creating playlists!

    You must have a premium Spotify membership to continue.

    You will also need to grant Spotty access to build your playlist.

    Accept in your browser and paste the redirect URL in the terminal. 

    ''')


    @click.command()
    @click.argument('username', required=True, nargs=1, type=click.STRING)
    def parse_args(username):
        SubredditPlaylistBuilder(username)

    parse_args()
