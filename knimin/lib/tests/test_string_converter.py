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
from unittest import TestCase, main
from knimin.lib.string_converter import Converter


class TestConverter(TestCase):
    def setUp(self):
        self.conv = Converter()

    def test_camel_to_snake(self):
        self.assertEqual(self.conv.camel_to_snake('snakesOnAPlane'),
                         'snakes_on_a_plane')
        self.assertEqual(self.conv.camel_to_snake('SnakesOnAPlane'),
                         'snakes_on_a_plane')
        self.assertEqual(self.conv.camel_to_snake('_Snakes_On_APlane_'),
                         '_snakes_on_a_plane_')
        self.assertEqual(self.conv.camel_to_snake('snakes_on_a_plane'),
                         'snakes_on_a_plane')
        self.assertEqual(self.conv.camel_to_snake('IPhoneHysteria'),
                         'i_phone_hysteria')
        self.assertEqual(self.conv.camel_to_snake('iPhoneHysteria'),
                         'i_phone_hysteria')
        self.assertEqual(self.conv.camel_to_snake('iPHONEHysteria'),
                         'i_phone_hysteria')
        self.assertEqual(self.conv.camel_to_snake('_iPHONEHysteria'),
                         '_i_phone_hysteria')
        self.assertEqual(self.conv.camel_to_snake('iPHONEHysteria_'),
                         'i_phone_hysteria_')

    def testCamelToDash(self):
        self.assertEqual(self.conv.camelToDash('snakesOnAPlane'),
                         'snakes-on-a-plane')
        self.assertEqual(self.conv.camelToDash('SnakesOnAPlane'),
                         'snakes-on-a-plane')
        self.assertEqual(self.conv.camelToDash('-Snakes-On-APlane-'),
                         '-snakes-on-a-plane-')
        self.assertEqual(self.conv.camelToDash('snakes-on-a-plane'),
                         'snakes-on-a-plane')
        self.assertEqual(self.conv.camelToDash('IPhoneHysteria'),
                         'i-phone-hysteria')
        self.assertEqual(self.conv.camelToDash('iPhoneHysteria'),
                         'i-phone-hysteria')
        self.assertEqual(self.conv.camelToDash('iPHONEHysteria'),
                         'i-phone-hysteria')
        self.assertEqual(self.conv.camelToDash('-iPHONEHysteria'),
                         '-i-phone-hysteria')
        self.assertEqual(self.conv.camelToDash('iPHONEHysteria-'),
                         'i-phone-hysteria-')

    def testSnakeToCamel(self):
        self.assertEqual(self.conv.snakeToCamel('_snakes_on_a_plane_'),
                         '_snakesOnAPlane_')
        self.assertEqual(self.conv.snakeToCamel('snakes_on_a_plane'),
                         'snakesOnAPlane')
        self.assertEqual(self.conv.snakeToCamel('Snakes_on_a_plane'),
                         'snakesOnAPlane')
        self.assertEqual(self.conv.snakeToCamel('snakesOnAPlane'),
                         'snakesOnAPlane')
        self.assertEqual(self.conv.snakeToCamel('I_phone_hysteria'),
                         'iPhoneHysteria')
        self.assertEqual(self.conv.snakeToCamel('i_phone_hysteria'),
                         'iPhoneHysteria')
        self.assertEqual(self.conv.snakeToCamel('i_PHONE_hysteria'),
                         'iPHONEHysteria')
        self.assertEqual(self.conv.snakeToCamel('_i_phone_hysteria'),
                         '_iPhoneHysteria')
        self.assertEqual(self.conv.snakeToCamel('i_phone_hysteria_'),
                         'iPhoneHysteria_')

    def testDashToCamel(self):
        self.assertEqual(self.conv.dashToCamel('-snakes-on-a-plane-'),
                         '-snakesOnAPlane-')
        self.assertEqual(self.conv.dashToCamel('snakes-on-a-plane'),
                         'snakesOnAPlane')
        self.assertEqual(self.conv.dashToCamel('Snakes-on-a-plane'),
                         'snakesOnAPlane')
        self.assertEqual(self.conv.dashToCamel('snakesOnAPlane'),
                         'snakesOnAPlane')
        self.assertEqual(self.conv.dashToCamel('I-phone-hysteria'),
                         'iPhoneHysteria')
        self.assertEqual(self.conv.dashToCamel('i-phone-hysteria'),
                         'iPhoneHysteria')
        self.assertEqual(self.conv.dashToCamel('i-PHONE-hysteria'),
                         'iPHONEHysteria')
        self.assertEqual(self.conv.dashToCamel('-i-phone-hysteria'),
                         '-iPhoneHysteria')
        self.assertEqual(self.conv.dashToCamel('i-phone-hysteria-'),
                         'iPhoneHysteria-')


if __name__ == '__main__':
    main()
