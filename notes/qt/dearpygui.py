# import dearpygui.dearpygui as dpg

# def save_callback():
#     print("Save Clicked")

# dpg.create_context()
# dpg.create_viewport()
# dpg.setup_dearpygui()

# with dpg.window(label="Example Window"):
#     dpg.add_text("Hello world")
#     dpg.add_button(label="Save", callback=save_callback)
#     dpg.add_input_text(label="string")
#     dpg.add_slider_float(label="float")

# dpg.show_viewport()
# dpg.start_dearpygui()
# dpg.destroy_context()

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Sample data
np.random.seed(0)
dates = pd.date_range('20230101', periods=100)
data = pd.DataFrame(np.random.randn(100, 1), index=dates, columns=['Value'])

# Plot the data
fig, ax = plt.subplots()
data['Value'].plot(ax=ax)

# Number of indexes to highlight
highlight_last_x = 10

# Highlight the last x indexes
last_index = len(data) - 1
start_highlight = last_index - highlight_last_x + 1
ax.axvspan(data.index[start_highlight], data.index[last_index], color='lightgrey', alpha=0.5)

plt.show()