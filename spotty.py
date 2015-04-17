# coding=utf-8

import argparse
import praw
import re
import spotify as sp
import getpass
import threading
import os
import platform
import requests
import time
import datetime


class PlaylistBuilder:
    def __init__(self, sub_reddit, key_location=""):

        self._sub_reddit = sub_reddit
        self._playlist = None
        self._key_location = key_location
        self._scraped_tracks = []
        self._potential_tracks = None
        self._session = None

    @property
    def playlist(self):
        if self._playlist is None:
            print('A playlist is yet to be created.')
        return self._playlist

    @property
    def keylocation(self):
        return self._keylocation

    @keylocation.setter
    def keylocation(self, value):
        self._keylocation = value

    @property
    def sub_reddit(self):
        return self._sub_reddit

    def os_default(self, _platform):
        """
        Helper returning default locations for OSes.
        """
        return {
            'Darwin': '/Users/%s/spotify_appkey.key' % (os.getlogin()),
            'Linux': '/home/%s/spotify_appkey.key' % (os.getlogin()),
        }[_platform]

    def key_location_setup(self):
        """
        Method to locate and setup a users Spotify key. Location is defaulted to
        a user's home directory, unless specified otherwise using the positional
        argument 'keyfile'.

        Default Locations:

        Mac:
                /Users/*USER*/spotify_appkey.key

        Linux:
                /home/*USER*/spotify_appkey.key
        """

        if not self._key_location:
            config = sp.Config()
            config.user_agent = 'Spotty v0.1'
            self._key_location = self.os_default(platform.system())
            config.load_application_key_file(filename=self._key_location)
            return config

        elif self._key_location:
            config = sp.Config()
            config.user_agent = 'Spotty v0.1'
            config.load_application_key_file(filename=self._key_location)
            return config

        else:
            print("You Entered an invalid response, try again.")
            key_location_setup()

    def session_init(self):
        """
        Method to initialise a session with Spotify using credentials input
        by the user and a spotify_appkey file, which is passed to the session
        configuration as the new Spotify session object is initialised.
        """

        try:
            logged_in_event = threading.Event()
            session = sp.Session(config=self.key_location_setup())
            username = raw_input('Username: ')
            password = getpass.getpass('Password: ')
            session.login(username, password, remember_me=True)

            loop = sp.EventLoop(session)
            loop.start()

            def connection_state_listener(_session):
                """
                Helper function to awaken waiting threads.
                """
                if session.connection.state is sp.ConnectionState.LOGGED_IN:
                    logged_in_event.set()
                elif session.connection.state is sp.ConnectionState.LOGGED_OUT:
                    logged_in_event.set()

            """
            Registration of a listener for the session that will be triggered
            upon a CONNCECTION_STATE_UPDATED event. The
            connection_state_listener will be triggered, if LOGGED_IN, the
            thread will awaken.
            """
            session.on(sp.SessionEvent.CONNECTION_STATE_UPDATED,
                       connection_state_listener)

            self._session = session

        except Exception:

            print(Exception)

    def sub_scraper(self):
        """
        Method for scraping all potential tracks from a subreddit. This is
        currently defaulted to 'listentothis' and scrapes top posts from the
        last week. All done using the praw package.
        """

        try:
            r = praw.Reddit(user_agent='Spotty v0.1')
            self._potential_tracks = r.get_subreddit(
                self._sub_reddit).get_top_from_week(limit=100)

        except requests.HTTPError as e:

            if e.errno in [429, 500, 502, 503, 504]:
                print("Reddit is down (error %s), sleeping..." % e.errno)
                time.sleep(60)
                pass
            else:
                raise

        except Exception as e:

            print("couldn't Reddit: %s" % str(e))
            raise

        def track_grabber(self):
            """
            Helper for validating 'artist - title' structure of scraped posts.
            """
            for submission in self._potential_tracks:

                if re.match('\d{0,5} :: (\w.+) \-\-?', str(submission)):
                    artist = re.match('\d{0,5} :: (\w.+) \-\-?',
                                      str(submission))
                    if re.match('\w.+ --? (\w.+) \[', str(submission)):
                        title = re.match('\w.+ --? (\w.+) \[', str(submission))
                    else:
                        continue
                else:
                    continue

                # Add valid titles to list
                self._scraped_tracks.append([artist.group(1), title.group(1)])

        track_grabber(self)

    def search(self):
        """
        Use scraped tracks from subreddit to create a playlist.
        """
        # Create new playlist with subreddit as title
        container = self._session.playlist_container
        container.load()
        new_playlist = container.add_new_playlist(
            self.sub_reddit + " - " + str(datetime.date.today()))

        # Check tracks exist on Spotify, and if they do, add them to playlist
        print("\nAdding tracks to playlist '%s - %s'...\n" %
              (self.sub_reddit, datetime.date.today()))

        for track in self._scraped_tracks:
            searchtrack = self._session.search('artist:"%s" title:"%s"' %
                                               (track[0], track[1])).load()
            if len(searchtrack.tracks) >= 1:
                print(searchtrack.tracks[0].name + ' - ' +
                      searchtrack.tracks[0].artists[0].load().name)
                new_playlist.add_tracks(searchtrack.tracks[0])

        self._playlist = new_playlist

        print(
            "\nThanks for using Spotty. Now go and rock out to your brand new"
            " playlist!")


def main():
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

    You will also need your API token found here:

        http://devaccount.spotify.com/my-account/keys/

    Download your key and store it in your user directory!

    ''')

    parser = argparse.ArgumentParser(description='Spotty')
    parser.add_argument('keyfile',
                        nargs='?',
                        help='Specify the location of your keyfile.')
    args = parser.parse_args()

    if args.keyfile:
        new_playlist = PlaylistBuilder('listentothis', args.keyfile)
    else:
        new_playlist = PlaylistBuilder('listentothis')

    new_playlist.key_location_setup()
    new_playlist.session_init()
    new_playlist.sub_scraper()
    new_playlist.search()

if __name__ == "__main__":
    main()

