#!/usr/bin/env python

"""
Finds all HTML instances of STATIC_URL in templates and converts to use the
static template tag instead.
"""

from __future__ import print_function

import argparse
import os
import re
import sys

file_formats = [".html", ".txt"]


def _static_url_replacement(match):
    groups = match.groups()
    assert "{" not in groups[1], groups[1]
    return "{{% static '{name}' %}}{close}".format(name=groups[1],
                                                   close=groups[2])


class Converter(object):

    LOAD_STATIC_REGEX = re.compile(r"{% ?load staticfiles ?%}")
    STATIC_URL_REGEX = re.compile(r"({{ ?STATIC_URL ?}})(.*?)([{\'\"])")

    def __init__(self, dry_run=False, output=sys.stdout):
        self.dry_run = dry_run
        self.output = output

    def _get_template_files(self, directory):
        for cd, unused, files in os.walk(directory):
            for filename in files:
                if os.path.splitext(filename)[1] in file_formats:
                    yield os.path.join(cd, filename)


    def _static_library_loaded(self, contents):
        """Scan file to see if the static library is loaded"""
        return self.LOAD_STATIC_REGEX.search(contents) is not None

    def _get_static_url_count(self, contents):
        """Scan file to see how many static URL(s) it contains"""
        return len(self.STATIC_URL_REGEX.findall(contents))

    def convert_contents(self, contents, add_static_import=False):
        if add_static_import:
            line_no = 0
            lines = contents.split(os.linesep)
            for line in lines:
                is_blank = line.strip() == ""
                extends_tag = (line.startswith("{%extends")
                               or line.startswith("{% extends"))
                load_tag = (line.startswith("{%load")
                            or line.startswith("{% load"))
                if not (is_blank or extends_tag or load_tag):
                    break
                line_no += 1
            while line_no > 0 and lines[line_no - 1].strip() == "":
                line_no -= 1
            lines.insert(line_no, "{% load static %}")
            contents = os.linesep.join(lines)
        contents = self.STATIC_URL_REGEX.sub(_static_url_replacement, contents)
        return contents

    def _write_file(self, filename, contents, add_static_import=False,
                    converted_tags=0):
        if add_static_import:
            print("Adding staticfiles import to %s..." % filename,
                  file=self.output)
        if converted_tags > 0:
            msg = "Converting %d STATIC_URL(s) to static tags in %s" % (
                converted_tags, filename)
            print(msg, file=self.output)
        if self.dry_run:
            return
        with open(filename, "w") as fh:
            fh.write(contents)

    def find_and_convert(self, root_dir):
        for filename in self._get_template_files(root_dir):
            with open(filename) as fh:
                contents = fh.read()
            static_urls = self._get_static_url_count(contents)
            if static_urls > 0:
                add_static_import = not self._static_library_loaded(contents)
                contents = self.convert_contents(contents, add_static_import)
                self._write_file(filename, contents, add_static_import,
                                 static_urls)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("location", help="Root of Django project")
    parser.add_argument("-n", "--dry-run", dest="dry_run", action="store_true",
                        help="Dry run (no-op)")
    options = parser.parse_args(argv)
    return Converter(options.dry_run).find_and_convert(options.location)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
