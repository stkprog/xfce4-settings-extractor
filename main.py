# A python script that grabs all XFCE4 settings using xfconf-query
# and saves them into a .sh-file which can be used to restore
# those exact configurations.
# Copyright (C) 2024 St. K.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os       # To use shell commands
import typing   # Type hinting
import sys      # To use command line arguments
import re       # Regular expressions

def get_channel_header(channel_name : str) -> str:
    """Returns a nice header for the current channel in the output script."""
    header = "#\n"
    header += "#    Channel: " + channel_name + "\n"
    header += "#\n"
    return header

def get_all_channels() -> list:
    """Get all available channels using the shell command xfconf-query."""
    needed_channels = []
    if "-a" in sys.argv or "--all" in sys.argv:
        needed_channels = [
            "displays", "keyboard-layout", "keyboards", "parole", "pointers", "ristretto", "thunar", "thunar-volman", "xfce4-appfinder", "xfce4-desktop", "xfce4-keyboard-shortcuts", "xfce4-notifyd", "xfce4-panel", "xfce4-power-manager", "xfce4-screensaver", "xfce4-screenshooter", "xfce4-session", "xfce4-taskmanager", "xfce4-terminal", "xfwm4", "xsettings"
        ]
    else:
        needed_channels = ["xfce4-desktop", "xfce4-panel", "xfce4-terminal", "xfwm4", "xsettings", "xfce4-notifyd"]
    
    # Get all channels in the form of a list
    result = os.popen("xfconf-query -l").read().splitlines()

    # The first line is not a channel, pop it
    result.pop(0)

    # keep only the needed channels
    new_result = []
    for line in range(len(result)):
        # remove whitespace from the left
        line_stripped = result[line].strip()
        if line_stripped in needed_channels:
            new_result.append(line_stripped)

    return new_result

def get_all_properties_of_channel(channel_name : str) -> list:
    """Get all available properties for the specified channel"""
    # Get all properties in the form of a list
    result = os.popen("xfconf-query -c " + channel_name + " -l").read().splitlines()

    for line in range(len(result)):
        line_content = result[line]

        if "<" in line_content or ">" in line_content:
            result[line] = insert_escape_backslash_at_angle_brackets(line_content)

    result = filter(lambda x : not x.startswith("/plugins/") and not x == "/general/button_layout", result)
    return result

def insert_escape_backslash_at_angle_brackets(to_be_converted : str) -> str:
    """Insert the escape character at angle brackets so the resulting shell script will work."""
    return to_be_converted.replace("<", "\\<").replace(">", "\\>")

def handle_array(property_value : str) -> list:
    """Process a property holding an array of values, rather than a single value, correctly."""
    # Split the string into an array of lines
    value_array = property_value.splitlines()
    # Pop the first two because they're irrelevant
    value_array.pop(0)
    value_array.pop(0)

    for line in range(len(value_array)):
        print("\n\n" + value_array[line] + " -> ")
        if is_numeric(value_array[line]):
            value_array[line] = handle_numeric(value_array[line])
        else:
            value_array[line] = "\"" + value_array[line].strip("\n") + "\""

    return value_array

def is_numeric(value : str) -> bool:
    """Check if the given string is numeric."""
    # print(re.search("[+0-9],[+0-9]", value) is not None or value.strip().isdecimal())
    if re.search("[+0-9],[+0-9]", value) is not None or value.isdecimal():
        return True
    else:
        return False

def handle_numeric(value : str) -> bool:
    """Convert commas (,) in the given string to dots (.)."""
    return value.replace(",", ".")

def handle_rgb(rgb_array : list) -> list:
    """
    Returns a hex-value array based on an array of rgb-values.
    E.g.: ["rgb(255,255,255)", "rgb(0, 0, 0)"] is converted to ["#FFFFFF", "#000000"].
    """
    hex_array = []
    for value in rgb_array:
        hex_array.append(rgb_to_hex(value))
    return hex_array

def rgb_to_hex(rgb_string : str) -> str:
    """
    Returns a hex-value based on an rgb-value.
    E.g.: "#FF00FF" is converted to "rgb(255,0,255)".
    """
    tuple = re.findall(r"[0-9]+", rgb_string)
    r = int(tuple[0])
    g = int(tuple[1])
    b = int(tuple[2])
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


# Main Script

# Check if user has given a scriptname, if not, quit the program
if len(sys.argv) < 2:
    print("\nYou need to include a name for your resulting script!")
    print("E.g.:")
    print("> python xfce4-theme-extractor cool_settings\n")
    quit()
elif len(sys.argv) > 3:
    print("\nInvalid amount of arguments.")
    quit()

# Regular expression used for finding RGB values
RGB_REGEX = r"rgb\([0-9]+,{1}[0-9]+,{1}[0-9]+\)"

# Holds the entire shell script that gets genereated in the form of a string
final_script_content = ""

# If it's the first loop, newlines won't be printed
first = True

# Loop through every channel
for channel in get_all_channels():
    if first is True:
        first = False
    else:
        final_script_content += "\n\n"

    final_script_content += get_channel_header(channel)

    # Loop through every property in the current channel
    for property in get_all_properties_of_channel(channel):
        final_script_content += "xfconf-query -c " + channel + " -p " + property
        property_value = os.popen("xfconf-query -c " + channel + " -p " + property).read()

        # Handle RGB values   
        if re.search(RGB_REGEX, property_value) is not None:
            old_values = re.findall(RGB_REGEX, property_value)
            # concatenate list elements with ; as separator
            old_string = ";".join(old_values)
            new_values = handle_rgb(re.findall(RGB_REGEX, property_value))
            new_string = ";".join(new_values)
            property_value = property_value.replace(old_string, new_string)

        # Handle arrays
        if "Wert ist ein Feld mit" in property_value:
            property_value = handle_array(property_value)
            for line in property_value:
                final_script_content += " -s " + line
        # Everything else
        else:
            if is_numeric(property_value):
                print("\n\n" + property_value + " -> ")
                property_value = handle_numeric(property_value)
            else:
                property_value = "\"" + property_value.strip("\n") + "\""
            final_script_content += " -s " + property_value

        final_script_content += "\n"

# Write script string to file
script_name = ""
if (sys.argv[1] == "-a" or sys.argv[1] == "--all"):
    script_name = sys.argv[2]
else:
    script_name = sys.argv[1]
final_script = open(script_name + ".sh", "w")
final_script.write(final_script_content)
final_script.close()