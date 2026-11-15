from argparse import ArgumentParser
from ghapi.all import GhApi

argparser = ArgumentParser(description="Judge a program based on the configuration.")

argparser.add_argument("-r", "--config-repo", help="The config repo.")
argparser.add_argument("-t", "--token", help="The bot token.")
