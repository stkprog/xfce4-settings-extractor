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
import click    # For creating a neat command line interface with options / flags
import re       # Regular expressions

def get_channel_header(channel_name : str) -> str:
    """Returns a nice header for the current channel in the output script."""
    header : str = "#\n"
    header += "#    Channel: " + channel_name + "\n"
    header += "#\n"
    return header

def get_needed_channels(get_all : bool) -> list[str]:
    """Get the specified channels using the shell command xfconf-query."""
    all_channels : list[str] = []
    needed_channels : list[str] = []
    all_channels = os.popen("xfconf-query -l").read().splitlines()
    all_channels.pop(0) # First line just reads "Channels:", unneeded
    for i in range(len(all_channels)):
        all_channels[i] = all_channels[i].strip()

    # Get all channels
    if get_all == True:
        needed_channels = all_channels
    # Only get channels for "visual" configurations
    else:
        visuals_channels : list[str] = ["xfce4-desktop", "xfce4-panel", "xfce4-terminal", "xfwm4", "xsettings", "xfce4-notifyd"]
        # Check if these channels are available on the current system
        for c in visuals_channels:
            if c in all_channels:
                needed_channels.append(c)

    return needed_channels

def get_all_properties_of_channel(channel_name : str) -> list[str]:
    """Get all available properties for the specified channel"""
    # Get all properties in the form of a list
    result : list[str] = os.popen("xfconf-query -c " + channel_name + " -l").read().splitlines()

    for line in range(len(result)):
        line_content : str = result[line]

        if "<" in line_content or ">" in line_content:
            result[line] = insert_escape_backslash_at_angle_brackets(line_content)

    return result

def insert_escape_backslash_at_angle_brackets(to_be_converted : str) -> str:
    """Insert the escape character at angle brackets so the resulting shell script will work."""
    return to_be_converted.replace("<", "\\<").replace(">", "\\>")

def insert_escape_backslash_at_double_quote(to_be_converted : str) -> str:
    """Insert the escape character at double quotes so the resulting script will set the correct values."""
    return to_be_converted.replace("\"", "\\\"")

def handle_array(property_value : str) -> list[str]:
    """Process a property holding an array of values, rather than a single value, correctly."""
    # Split the string into an array of lines
    value_array : list[str] = property_value.splitlines()
    # Pop the first two because they're irrelevant
    value_array.pop(0)
    value_array.pop(0)
    
    for line in range(len(value_array)):
        # If the current line in the value array is a number, replace commas with dots
        if is_numeric(value_array[line]):
            value_array[line] = handle_numeric(value_array[line])
        # If the current line in the value array is a string, add double quotes around it and remove new line character
        else:
            # If there's double quotes already present, add escape character
            if "\"" in value_array[line]:
                value_array[line] = insert_escape_backslash_at_double_quote(value_array[line])
            # Add double quotes around whole string and remove new line character
            value_array[line] = "\"" + value_array[line].strip("\n") + "\""

    return value_array

def is_numeric(value : str) -> bool:
    """Check if the given string is numeric."""
    if re.search("[+0-9],[+0-9]", value) is not None or value.isdecimal():
        return True
    else:
        return False

def handle_numeric(value : str) -> bool:
    """Convert commas (,) in the given string to dots (.)."""
    return value.replace(",", ".")

def handle_rgb(rgb_array : list[str]) -> list[str]:
    """
    Returns a hex-value array based on an array of rgb-values.
    E.g.: ["rgb(255,255,255)", "rgb(0, 0, 0)"] is converted to ["#ffffff", "#000000"].
    """
    hex_array : list[str] = []
    for value in rgb_array:
        hex_array.append(rgb_to_hex(value))
    return hex_array

def rgb_to_hex(rgb_string : str) -> str:
    """
    Returns a hex-value based on an rgb-value.
    E.g.: "#ff00ff" is converted to "rgb(255,0,255)".
    """
    tuple = re.findall(r"[0-9]+", rgb_string)
    r = int(tuple[0])
    g = int(tuple[1])
    b = int(tuple[2])
    # x == lowercase hexadecimal
    # 02 == string should be left-filled with zeroes to a length of 2 if needed
    return "#{:02x}{:02x}{:02x}".format(r, g, b)

def check_script_name(script_name : str) -> str:
    """Appends '.sh' to the end of the script name if the file extension is not given yet."""
    if not script_name.endswith(".sh"):
        script_name += ".sh"
    return script_name

def get_destination_path(output : click.Path, script_name : str) -> str:
    """Combines the destination path and the script name."""
    if (not str(output).endswith("/")) and not script_name.startswith("/"):
        output += "/"
    return output + script_name

def main_loop(all_channels : bool) -> str:
    """
    Main loop of the program.
    Returns a string containing the content of the
    finished shell script, using the utility functions
    in this program to do so.
    """
    # Regular expression used for finding RGB values
    RGB_REGEX : str = r"rgb\([0-9]+,{1}[0-9]+,{1}[0-9]+\)"

    # Holds the entire shell script that gets genereated in the form of a string
    final_script_content : str = ""

    # If it's the first loop, newlines won't be printed
    first : bool = True

    # These properties of the thunar channel hold a string-value
    # containing a comma-separated list of numbers
    # As such, values of these properties should NOT be processed by handle_numeric()
    # A dot-seperated list in these settings can / will prevent Thunar from starting
    comma_separated_settings = ["/last-toolbar-item-order", "/last-toolbar-visible-buttons", "/last-details-view-column-widths"]

    # Loop through every channel
    for channel in get_needed_channels(all_channels):
        # Space between channels, but not on the first one
        if first is True:
            first = False
        else:
            final_script_content += "\n\n"

        final_script_content += get_channel_header(channel)

        # Loop through every property in the current channel
        for property in get_all_properties_of_channel(channel):
            final_script_content += "xfconf-query -c " + channel + " -p " + property
            property_value : str = os.popen("xfconf-query -c " + channel + " -p " + property).read()

            # Handle RGB values   
            if re.search(RGB_REGEX, property_value) is not None:
                old_values : list[str] = re.findall(RGB_REGEX, property_value)
                # concatenate list elements with ; as separator
                old_string : str = ";".join(old_values)
                new_values : list[str ]= handle_rgb(re.findall(RGB_REGEX, property_value))
                new_string : str = ";".join(new_values)
                property_value : str = property_value.replace(old_string, new_string)

            # Handle arrays
            property_value_lines : int = len(property_value.splitlines())
            # Output such as "Value is an array with 1 items: \n\n value_1" has THREE lines
            if property_value_lines >= 3:
                property_value = handle_array(property_value)
                # Every item in the array must be added individually like this
                for line in property_value:
                    final_script_content += " -s " + line
                # If value is an array with one item, add this needed flag
                if property_value_lines == 3:
                    final_script_content += " --force-array "
            # Everything else
            else:
                # If the current value is a number, replace commas with dots
                if is_numeric(property_value) and property not in comma_separated_settings:
                    property_value = handle_numeric(property_value)
                # If the current line in the value array is a string, add double quotes around it and remove new line character
                else:
                    # If there's double quotes already present, add escape character
                    if "\"" in property_value:
                        property_value = insert_escape_backslash_at_double_quote(property_value)
                    # Add double quotes around whole string and remove new line character
                    property_value = "\"" + property_value.strip("\n") + "\""
                final_script_content += " -s " + property_value

            final_script_content += "\n"
    return final_script_content

# Make sure that "-h" is a valid option as well
CLICK_SETTINGS : dict = dict(help_option_names=["-h", "--help"])
@click.command(context_settings=CLICK_SETTINGS)
@click.option(
    "-a", "--all",
    help="Extract settings from all available xfconf channels.\nDefault: Only visual channels.",
    is_flag=True    # False if --all is not set, True if it is
)
@click.option(
    "-o", "--output",
    help="Destination of the .sh-script.                   \nDefault: Current working directory.",
    type=click.Path(file_okay=False, dir_okay=True, readable=True, writable=True, exists=True),
    default="."
)
@click.argument("script_name")
def enter(all : bool, output : click.Path, script_name : str):
    """Entrypoint of the program. Uses the parameters from the click options / arguments."""
    script_name = check_script_name(script_name)
    
    final_path : str = get_destination_path(output, script_name)
    final_script_content : str = main_loop(all)

    # Write script string to file
    with open(final_path, "w") as final_script:
        final_script.write(final_script_content)

enter()