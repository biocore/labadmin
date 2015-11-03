#!/usr/bin/env python
"""
  Convert camel-case to snake-case in python.
  e.g.: CamelCase  -> snake_case
  e.g.: snake_case -> CamelCase
  e.g.: CamelCase  -> dash-case
  e.g.: dash-case  -> CamelCase
  By:            Jay Taylor [@jtaylor]
  Me<modifier>:  Yahya Kacem <fuj.tyoli@gmail.com>
  Original gist: https://gist.github.com/jaytaylor/3660565
"""
import re


class Converter(object):
    _first_cap_re = re.compile(r'(.)([A-Z][a-z]+)')
    _all_cap_re = re.compile('([a-z0-9])([A-Z])')

    def camel_to_snake(self, camelCasedStr):
        """
        This function converts to snake_case from camelCase
        """
        sub1 = self._first_cap_re.sub(r'\1_\2', camelCasedStr)
        snake_cased_str = self._all_cap_re.sub(r'\1_\2', sub1).lower()
        return snake_cased_str.replace('__', '_')

    def camelToDash(self, camelCasedStr):
        """
        This function converts to dashed_case from camelCase
        """
        sub2 = self._first_cap_re.sub(r'\1-\2', camelCasedStr)
        dashed_case_str = self._all_cap_re.sub(r'\1-\2', sub2).lower()
        return dashed_case_str.replace('--', '-')

    def snakeToCamel(self, snake_cased_str):
        return self._convertToCamel(snake_cased_str, "_")

    def dashToCamel(self, snake_cased_str):
        return self._convertToCamel(snake_cased_str, "-")

    def _convertToCamel(self, snake_cased_str, separator):
        components = snake_cased_str.split(separator)
        preffix = ""
        suffix = ""
        if components[0] == "":
            components = components[1:]
            preffix = separator
        if components[-1] == "":
            components = components[:-1]
            suffix = separator
        if len(components) > 1:
            camelCasedStr = components[0].lower()
            for x in components[1:]:
                if x.isupper() or x.istitle():
                    camelCasedStr += x
                else:
                    camelCasedStr += x.title()
        else:
            camelCasedStr = components[0]
        return preffix + camelCasedStr + suffix

converter = Converter()
