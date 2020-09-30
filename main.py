import curses
import queue
import string
import subprocess
import threading
import time
from datetime import datetime

state = {}
threads = []

result_pipeline = queue.Queue()
instr_pipeline = queue.Queue()


def execute_zowe_workload():
    """
    This function is carried out in a separate thread as the zowe calls take a while to complete and
    we want to try and block as little as possible.
    :return:
    """
    global instr_pipline
    global result_pipeline
    try:
        t = threading.currentThread()
        current_instruction = None
        last_run_instruction = 0
        item = None
        while getattr(t, "do_run", True):
            if not instr_pipeline.empty():
                item = instr_pipeline.get(False)
            if current_instruction is not None or item is not None:
                if item != current_instruction or \
                        last_run_instruction == 0 or \
                        time.time() - last_run_instruction > 10:
                    if item is not None:
                        current_instruction = item
                        item = None
                    msg = None
                    if "delete" in current_instruction:
                        output = execute_zowe_command(current_instruction)
                        msg = output
                        current_instruction = "zowe jobs list jobs"
                    output = execute_zowe_command(current_instruction)
                    jobs = parse_job_list(output)
                    result_pipeline.put({"type": "jobs", "data": jobs, "timestamp": time.time(), "editor.msg": msg})
                    last_run_instruction = time.time()
            time.sleep(0.25)
    except Exception as err:
        print(err)


def request_job_list():
    cmd = "zowe zos-jobs list jobs"
    execute_zowe_command(cmd)


def execute_zowe_command(cmd: str):
    process = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text="text")
    return process.stdout

def add_shortcut_keys_based_on_job_type(jobs):
    global state
    keys = state["shortcut_keys"]
    menu = ""
    for key in jobs.keys():
        menu = menu + "[{}]{} ".format(key[0], key[1:])
        keys[key[0].lower()] = key
    state["shortcut_keys"] = keys


def create_top_menu_shortcuts(jobs):
    menu = ""
    for key in jobs.keys():
        menu = menu + "[{}]{} ".format(key[0], key[1:])
    return menu


def update_top_shortcuts_menu(jobs):
    add_shortcut_keys_based_on_job_type(jobs)
    menu = create_top_menu_shortcuts(jobs)
    state["window_tree"]["top_menu"].bkgd(' ', curses.color_pair(2))
    state["window_tree"]["top_menu"].addstr(0, 1, menu, curses.color_pair(2))
    state["window_tree"]["top_menu"].refresh()


def update_main_window(jobs):
    """
    Update the main window listing
    :param jobs:
    :return:
    """
    state["window_tree"]["main"].clear()
    heading = "{:3} {:10}{:10}{:15}{:10}".format("Job", "ID", "Type", "Name", "Status")
    state["window_tree"]["main"].addstr(2, 1, heading)
    horizontal_line = u"\u2015" * int(state["window_tree"]["main"].getmaxyx()[1])
    state["window_tree"]["main"].addstr(3, 0, horizontal_line)

    cur_y = 4
    if state["job_type"] in jobs:
        for job in jobs[state["job_type"]]:
            try:
                state["window_tree"]["main"].addstr(cur_y, 1,
                                                    '{:03d} {:10}{:10}{:15}{:10}'.format(job["_num"], job["id"],
                                                                                         job["type"], job["name"],
                                                                                         job["status"]))
            except:
                pass
            cur_y += 1
    state["window_tree"]["main"].refresh()
    state["zowe_state"] = "READY"


def parse_job_list(stdout_text):
    lines = stdout_text.split("\n")
    jobs = {}

    for l in lines:
        if len(l.strip()) > 0:
            l = ' '.join(l.split())
            columns = l.split(" ")
            if len(columns) == 5:
                job_class = columns[0][0:3].strip().upper()
                job_id = columns[0].strip()
                job_status = "{} {}".format(columns[1].strip(), columns[2].strip())
                job_name = columns[3].strip()
                job_type = columns[4].strip()
            elif len(columns) == 4:
                job_class = columns[0][0:3].strip().upper()
                job_id = columns[0].strip()
                job_status = columns[1].strip()
                job_name = columns[2].strip()
                job_type = columns[3].strip()
            elif len(columns) == 3:
                job_class = columns[0][0:3].strip().upper()
                job_id = columns[0].strip()
                job_status = "N/A"
                job_name = columns[1].strip()
                job_type = columns[2].strip()
            else:
                raise ValueError("unexpected number of columns in zowe jobs output")
            if job_class not in jobs:
                jobs[job_class] = []
            jobs[job_class].append(
                {"_num": len(jobs[job_class]) + 1, "class": job_class, "id": job_id, "status": job_status,
                 "name": job_name, "type": job_type})
    return jobs


def define_windows(stdscr):
    # height, width, y, x
    # top of screen
    title = curses.newwin(1, stdscr.getmaxyx()[1] - 25, 0, 0)
    timer_window = curses.newwin(1, 25, 0, stdscr.getmaxyx()[1] - 25)
    top_menu = curses.newwin(1, stdscr.getmaxyx()[1], 1, 0)
    # bottom of screen
    edit_window = curses.newwin(1, stdscr.getmaxyx()[1], stdscr.getmaxyx()[0] - 2, 0)
    footer_window = curses.newwin(1, stdscr.getmaxyx()[1] - 40, stdscr.getmaxyx()[0] - 1, 0)
    footer_window_right = curses.newwin(1, stdscr.getmaxyx()[1], stdscr.getmaxyx()[0] - 1, stdscr.getmaxyx()[1] - 40)
    # middle of screen
    main_window = curses.newwin(stdscr.getmaxyx()[0] - 5, stdscr.getmaxyx()[1], 2, 0)
    return {"root": stdscr,
            "timer": timer_window,
            "title": title,
            "top_menu": top_menu,
            "main": main_window,
            "editor": edit_window,
            "footer": footer_window,
            "updated": footer_window_right
            }


def resize_windows(stdscr):
    stdscr.clear()
    return define_windows(stdscr)


def create_windows(stdscr):
    return define_windows(stdscr)


def update_menu_time(window_tree):
    window_tree["timer"].bkgd(' ', curses.color_pair(2))
    time_text = "    {}".format(time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        window_tree["timer"].addstr(0, 1, time_text, curses.color_pair(2))
    except:
        pass
    window_tree["timer"].refresh()


def update_edit_bar(window_tree):
    pass


def action(state, input):
    pass


def update_editor(msg):
    state["window_tree"]["editor"].clear()
    state["window_tree"]["editor"].bkgd(' ', curses.color_pair(2))
    try:
        state["window_tree"]["editor"].addstr(msg)
    except:
        pass
    state["window_tree"]["editor"].refresh()


def main(stdscr):
    """
    This is our main event loop and we only care about redrawing and getting user input

    :param stdscr:
    :return:
    """
    global state
    global instr_pipeline
    global result_pipeline

    state = {"job_type": "JOB", "zowe_state": "STARTING", "shortcut_keys": {}, "action": None}
    keys = {}
    curses.halfdelay(5)
    user_input = ""
    alphabet = string.printable

    # height, width, x, y
    window_tree = resize_windows(stdscr)
    state["window_tree"] = window_tree
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)

    instr_pipeline.put("zowe zos-jobs list jobs")
    curses.curs_set(0)
    while True:
        window_tree["root"].refresh()

        window_tree["updated"].bkgd(' ', curses.color_pair(2))
        window_tree["updated"].refresh()
        window_tree["top_menu"].bkgd(' ', curses.color_pair(2))
        window_tree["top_menu"].refresh()
        window_tree["editor"].bkgd(' ', curses.color_pair(2))
        window_tree["editor"].refresh()
        window_tree["updated"].bkgd(' ', curses.color_pair(2))
        window_tree["updated"].refresh()
        window_tree["footer"].bkgd(' ', curses.color_pair(2))
        window_tree["footer"].refresh()

        if not result_pipeline.empty():
            msg = result_pipeline.get(False)
            if msg is not None:
                if msg["type"] == "jobs":
                    state["jobs"] = msg["data"]
                    update_top_shortcuts_menu(msg["data"])
                    update_main_window(state["jobs"])
                    if msg["editor.msg"] is not None:
                        update_editor(msg["editor.msg"])
                elif msg["type"] == "editor":
                    update_editor(msg["data"])
                if msg is not None:
                    window_tree["updated"].bkgd(' ', curses.color_pair(2))
                    try:
                        window_tree["updated"].addstr(0, 1, "{} {:>}".format("Last Updated: ", datetime.fromtimestamp(
                            msg["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")), curses.color_pair(2))
                    except:
                        pass
                    window_tree["updated"].refresh()

        update_menu_time(window_tree)

        window_tree["title"].bkgd(' ', curses.color_pair(2))
        menu = "{} ".format("Zowe Terminal Explorer")
        try:
            window_tree["title"].addstr(0, 1, menu, curses.color_pair(2))
        except:
            pass
        window_tree["title"].refresh()

        window_tree["main"].bkgd(' ', curses.color_pair(1))
        window_tree["main"].refresh()

        window_tree["footer"].bkgd(' ', curses.color_pair(2))
        try:
            window_tree["footer"].addstr(0, 1, "[Q]uit  [D]elete", curses.color_pair(2))
        except:
            pass
        window_tree["footer"].refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            window_tree["root"].clear()
            window_tree = resize_windows(stdscr)
        else:
            changed = False
            if key != ord('q') and key in range(0x110000):
                ch = chr(key)
                if ch in state["shortcut_keys"]:
                    state["job_type"] = state["shortcut_keys"][ch]
                    update_top_shortcuts_menu(msg["data"])
                    update_main_window(state["jobs"])
                    changed = True

            if not changed:
                if key == 27:  # ESCAPE
                    state["action"] = None
                    user_input = None
                    update_editor("")
                elif key == ord('q'):
                    update_editor("Waiting for threads to shutdown...")
                    threads[0].do_run = False
                    threads[0].join()
                    return
                elif key in range(0x110000) and chr(key) in "0123456789" and state["action"] is not None:
                    user_input += chr(key)
                    update_editor(" Enter job number from first column: {}".format(user_input))
                elif key == ord('d') and state["action"] is None:
                    state["action"] = "d"
                    update_editor(" Enter job number from first column: ")
                elif key == curses.KEY_BACKSPACE and state["action"] is not None:
                    if len(user_input) > 0:
                        user_input = user_input[:-1]
                elif key == curses.KEY_ENTER or key == 10:
                    try:
                        job_num = int(user_input)
                        if state["action"] == "d":
                            valid_jobs = state["jobs"][state["job_type"]]
                            found = False
                            for j in valid_jobs:
                                if j["_num"] == job_num:
                                    update_editor("Deleting {} with job id '{}'".format(j["_num"], j["id"]))
                                    instr_pipeline.put("zowe jobs delete job {}".format(j["id"]))
                                    found = True
                                    break
                            if found == False:
                                update_editor(" {} is not a valid number.".format(job_num))
                            state["action"] = None
                            user_input = None
                        else:
                            update_editor(" Not a valid action.")
                            state["action"] = None
                            user_input = None
                    except ValueError as err:
                        update_editor(" Not a valid job number.")
                        state["action"] = None
                        user_input = None


def direct():
    """
    Used for testing without curses
    :return:
    """
    global instr_pipeline
    instr_pipeline.put("zowe zos-jobs list jobs")
    time.sleep(10)
    print(result_pipeline.get())


if __name__ == "__main__":
    """
    Main entry point
    """
    t = threading.currentThread()
    t = threading.Thread(target=execute_zowe_workload)
    t.do_run = True
    t.start()
    threads.append(t)
    # direct()
    curses.wrapper(main)
