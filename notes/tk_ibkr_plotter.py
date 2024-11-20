import tkinter as tk
from tkinter import ttk
from .strategy import strategies as strategy
from .strategy import indicators as indicator
from .trend_viewer import *
import os
import matplotlib.pyplot as plt
print(os.getcwd())

from ib_insync import *
import src.floor_ceiling_regime as fcr

port = 4001
ib = IB()
ib.connect('127.0.0.1', port, clientId=0)
run_manager = None

def on_confirm():
    global run_manager

    symbol = symbol_entry.get() or 'SPY'
    sec_type = sec_type_entry.get() or 'STK'
    interval = interval_combobox.get() or '1 day'
    duration = duration_combobox.get() or '3 Y'
    use_rth = use_rth_var.get()
    keep_up_to_date = keep_up_to_date_var.get()
    band_window = int(band_window_entry.get() or 233)
    peak_window = int(peak_window_entry.get() or 5)
    plot_window = int(plot_window_entry.get() or 1000)
    band_type = band_type_combobox.get() or 'Rolling'
    if band_type == 'Rolling':
        bandFunc = addBand
        peak_window = 0
    else:
        bandFunc = addBandAggregatePeakConcat

    intraday = ['1 secs', '5 secs', '10 secs', '15 secs', '30 secs', '1 min', '2 mins', '3 mins', '5 mins', '10 mins', '15 mins', '20 mins', '30 mins', '1 hour', '2 hours', '3 hours', '4 hours', '8 hours']
    if interval not in intraday:
        use_rth = True

    if run_manager is None:
        run_manager = IBRunManager(ib, Contract, strategy, indicator, util, lambda _: None)

    run_manager.run(
        bandFunc=bandFunc,
        symbol=symbol,
        sec_type=sec_type,
        interval=interval,
        duration=duration,
        use_rth=use_rth,
        keep_up_to_date=keep_up_to_date,
        band_window=band_window,
        peak_window=peak_window,
        plot_window=plot_window,
    )

# Create the main window
root = tk.Tk()
root.title("Run Profile Input")

# Create and place the input fields
ttk.Label(root, text="Symbol:").grid(row=0, column=0, padx=10, pady=5)
symbol_entry = ttk.Entry(root)
symbol_entry.grid(row=0, column=1, padx=10, pady=5)
symbol_entry.insert(0, 'SPY')  # Default value

ttk.Label(root, text="Security Type:").grid(row=1, column=0, padx=10, pady=5)
sec_type_entry = ttk.Entry(root)
sec_type_entry.grid(row=1, column=1, padx=10, pady=5)
sec_type_entry.insert(0, 'STK') # Default value

interval_options = [
    '1 secs', '5 secs', '10 secs', '15 secs', '30 secs', '1 min', '2 mins', '3 mins', '5 mins', '10 mins', 
    '15 mins', '20 mins', '30 mins', '1 hour', '2 hours', '3 hours', '4 hours', '8 hours', '1 day', '1 W', '1 M'
]
ttk.Label(root, text="Interval:").grid(row=2, column=0, padx=10, pady=5)
interval_combobox = ttk.Combobox(root, values=interval_options)
interval_combobox.grid(row=2, column=1, padx=10, pady=5)
interval_combobox.set('1 day')  # Default value

duration_options = ['1 day', '1 W', '1 M', '3 M', '6 M', '1 Y', '2 Y', '3 Y', '5 Y', '10 Y']
ttk.Label(root, text="Duration:").grid(row=3, column=0, padx=10, pady=5)
duration_combobox = ttk.Combobox(root, values=duration_options)
duration_combobox.grid(row=3, column=1, padx=10, pady=5)
duration_combobox.set('3 Y')  # Default value

use_rth_var = tk.BooleanVar()
ttk.Label(root, text="Use RTH:").grid(row=4, column=0, padx=10, pady=5)
use_rth_check = ttk.Checkbutton(root, variable=use_rth_var)
use_rth_check.grid(row=4, column=1, padx=10, pady=5)

keep_up_to_date_var = tk.BooleanVar()
ttk.Label(root, text="Keep Up To Date:").grid(row=5, column=0, padx=10, pady=5)
keep_up_to_date_check = ttk.Checkbutton(root, variable=keep_up_to_date_var)
keep_up_to_date_check.grid(row=5, column=1, padx=10, pady=5)

ttk.Label(root, text="Band Window:").grid(row=6, column=0, padx=10, pady=5)
band_window_entry = ttk.Entry(root)
band_window_entry.grid(row=6, column=1, padx=10, pady=5)

ttk.Label(root, text="Peak Window:").grid(row=7, column=0, padx=10, pady=5)
peak_window_entry = ttk.Entry(root)
peak_window_entry.grid(row=7, column=1, padx=10, pady=5)

ttk.Label(root, text="Plot Window:").grid(row=8, column=0, padx=10, pady=5)
plot_window_entry = ttk.Entry(root)
plot_window_entry.grid(row=8, column=1, padx=10, pady=5)

band_type_options = ['Rolling', 'Expanding']
ttk.Label(root, text="Band Type:").grid(row=9, column=0, padx=10, pady=5)
band_type_combobox = ttk.Combobox(root, values=band_type_options)
band_type_combobox.grid(row=9, column=1, padx=10, pady=5)
band_type_combobox.set('Rolling')  # Default value

# Create and place the confirm button
confirm_button = ttk.Button(root, text="Confirm", command=on_confirm)
confirm_button.grid(row=10, column=0, columnspan=2, pady=10)



# Run the application
root.mainloop()