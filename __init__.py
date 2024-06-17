'''
Copyright (C) 2024 Zach Eastin, Richard Traynor, Superhive

Created by Zach Eastin, Richard Traynor, Superhive

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
print()
print()
print(f"Loading {__package__.split('.')[-1].replace('_', ' ').title()}".center(80, '-'))
from . import ui, settings, ops, helpers


def _call_globals(attr_name):
    for m in globals().values():
        if hasattr(m, attr_name):
            getattr(m, attr_name)()


def register():
    print(f"Registering {__package__}")
    _call_globals("register")

    print(f"Finished Loading {__package__.split('.')[-1].replace('_', ' ').title()}".center(80, '-'))
    print()
    print()


def unregister():
    print(f"Unregistering {__package__}")
    _call_globals("unregister")