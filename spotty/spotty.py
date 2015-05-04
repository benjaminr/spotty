# coding=utf-8
import praw
import re
import spotify as sp
import getpass
import threading
import os
import sys
import platform
import requests
import time
import datetime
import click

class PlaylistBuilder:
    def __init__(self, sub_reddit, key_location=""):

        self._sub_reddit = sub_reddit
        self._playlist = None
        self._key_location = key_location
        self._scraped_tracks = []
        self._potential_tracks = None
        self._session = None

    @property
    def keylocation(self):
        return self._keylocation

    @keylocation.setter
    def keylocation(self, value):
        self._keylocation = value

    @property
    def playlist(self):
        if self._playlist is None:
            print('A playlist is yet to be created.')
        return self._playlist

    @property
    def sub_reddit(self):
        return self._sub_reddit

    def coroutine(func):
        def start(*args, **kwargs):
            cr = func(*args, **kwargs)
            next(cr)
            return cr

        return start

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

            def connection_state_listener(_session):
                """
                Helper function to awaken waiting threads.
                """
                if session.connection.state is sp.ConnectionState.LOGGED_IN:
                    logged_in_event.set()

            session = sp.Session(config=self.key_location_setup())
            loop = sp.EventLoop(session)
            loop.start()
            session.on(sp.SessionEvent.CONNECTION_STATE_UPDATED,
                       connection_state_listener)
            if sys.version_info.major == 2:
                username = raw_input('Username: ')
            elif sys.version_info.major == 3:
                username = input('Username: ')
            password = getpass.getpass('Password: ')
            session.login(username, password, remember_me=True)
            logged_in_event.wait()
            self._session = session

        except Exception as e:

            print(e, e.args)

    def reddit_connection(self):
        """
        Method for establishing a connection to Reddit using the PRAW library,
        returns a session object.
        """

        try:
            r = praw.Reddit(user_agent='Spotty v0.1')
            return r

        except requests.HTTPError as e:
            if e.errno in [429, 500, 502, 503, 504]:
                print("Reddit is down (error %s), sleeping..." % e.errno)
                time.sleep(60)
                pass
            else:
                raise e

        except Exception as e:
            print("couldn't Reddit: %s" % str(e))

    def reddit_scrape(self, session):
        """
        Method for scraping all potential tracks from a subreddit. This is
        currently defaulted to 'listentothis' and scrapes top posts from the
        last week. All done using the praw package. Submissions are sent to
        the track_validator coroutine.
        """

        t = self.track_validator()

        for submission in session.get_subreddit(
            self._sub_reddit).get_top_from_week(limit=100):
            t.send(submission)
        t.close()

    @coroutine
    def track_validator(self):
        """
        Check for title - artist structure in titles scraped from subreddit,
        sending valid ones to add_tracks_to_playlist coroutine.
        """
        attp = self.add_tracks_to_playlist()
        artistRegex = re.compile('\d{0,5} :: (\w.+) \-\-?')
        titleRegex = re.compile('\w.+ --? (\w.+) \[')
        try:
            while True:
                submission = (yield)
                if re.match(artistRegex, str(submission)):
                    artist = re.match(artistRegex, str(submission))
                    if re.match(titleRegex, str(submission)):
                        title = re.match(titleRegex, str(submission))
                        attp.send((artist, title))

        except GeneratorExit:
            attp.close()

    @coroutine
    def add_tracks_to_playlist(self):
        """
        Takes artist - title tuples sent from track_validator coroutine and
        searches for existence on Spotify. If they exist, they are added to
        the playlist.
        """

        try:
            while True:
                track = (yield)
                searchtrack = self._session.search(
                    'artist:"%s" title:"%s"' %
                    (track[0].group(1), track[1].group(1))).load()
                if len(searchtrack.tracks) >= 1:
                    print(searchtrack.tracks[0].name + ' - ' +
                          searchtrack.tracks[0].artists[0].load().name)
                    self._playlist.add_tracks(searchtrack.tracks[0])

        except GeneratorExit:
            print("=== Done ===")

    def build_playlist_container(self):
        """
        Use scraped tracks from subreddit to create a playlist.
        """
        # Create new playlist with subreddit as title
        built_container = self._session.playlist_container
        built_container.load()
        playlist = built_container.add_new_playlist(
            self.sub_reddit + " - " + str(datetime.date.today()))
        self._playlist = playlist


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

    def build_new_playlist(new_playlist):
        new_playlist.key_location_setup()
        new_playlist.session_init()
        new_playlist.build_playlist_container()
        new_playlist.reddit_scrape(new_playlist.reddit_connection())

    @click.command()
    @click.argument('keyfile', required=False, nargs=1, type=click.Path(exists=True))
    def parse_args(keyfile):
        if keyfile:
            click.echo("Keyfile: " + keyfile)
            build_new_playlist(PlaylistBuilder('listentothis', keyfile))
        else:
            if click.confirm('Did you mean to use the default key location?'):
                click.echo('You may continue...\n')
                build_new_playlist(PlaylistBuilder('listentothis'))
            else:
                keyfile = click.prompt('Please enter a keyfile location', type=click.Path(exists=True))
                build_new_playlist(PlaylistBuilder('listentothis', keyfile))

    parse_args()


if __name__ == "__main__":
    main()
