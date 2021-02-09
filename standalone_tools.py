import os
import inspect


from pathlib import Path


def eventlog(logstring):
    # if str(socket.gethostname()) == "tr3b":
    previous_frame = inspect.currentframe().f_back
    (filename, line_number, 
    function_name, lines, index) = inspect.getframeinfo(previous_frame)
    del previous_frame  # drop the reference to the stack frame to avoid reference cycles
    caller_filepath = filename
    caller_filepath = os.path.abspath(caller_filepath)
    caller_filename = ''
    for ch in caller_filepath:
        if not ch.isalnum():
            caller_filename += str('-')
        else:
            caller_filename += str(ch)
    if len(caller_filename) > 25:
        caller_filename = caller_filename[-25:]
    caller_filename += '_log.txt'
    debug_line_number = line_number
    if line_number < 10:
        debug_line_number = str('0000' + str(line_number))        
    elif line_number < 100:
        debug_line_number = str('000' + str(line_number))
    elif line_number < 1000:
        debug_line_number = str('00' + str(line_number))
    elif line_number < 10000:
        debug_line_number = str('0' + str(line_number))
    print(str(get_hour_minute_second_string()) + ' |==| ' + str(debug_line_number) + ' |==| ' + str(filename)[-25:] + ' | ' + str(function_name) + ' | ' + str(logstring) + ' |==|')

    with open(os.path.join(Path.cwd(), 'eventlog.log'), "a+") as f:
        f.write(str(get_hour_minute_second_string()) + ' |==| ' + str(debug_line_number) + ' |==| ' + str(filename)[-25:] + ' | ' + str(function_name) + ' | ' + str(logstring) + ' |==|')
        f.write('\n')

    if os.path.getsize(str(os.path.join(Path.cwd(), 'eventlog.log'))) > 1000000:
        with open(os.path.join(Path.cwd(), 'eventlog.log'), "w") as f:
            f.write('')
            f.close()



def get_hour_minute_second_string():
    from datetime import datetime
    now = datetime.now()
    dt_string = now.strftime("%H:%M:%S")
    return dt_string