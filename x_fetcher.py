import xmlrpc.client
import curses

# Define the hosts
hosts = [
    "http://localhost:8001/",
    "http://localhost:8002/",
    "http://localhost:8003/"
]

# XML-RPC function names
GET_FUNCTION = "get_x"
SET_FUNCTION = "set_x"

def call_rpc_function(hosts, function_name, *args):
    for host in hosts:
        server = xmlrpc.client.ServerProxy(host)
        try:
            function = getattr(server, function_name)
            result = function(*args)
            if result is not None:
                return result
        except Exception as e:
            continue
    return None

def tui(stdscr):
    curses.curs_set(1)
    stdscr.nodelay(0)

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        stdscr.addstr(0, 0, "Press 'g' to get value, 's' to set value, 'q' to quit")

        k = stdscr.getch()

        if k == ord('g'):
            value = call_rpc_function(hosts, GET_FUNCTION)
            stdscr.addstr(2, 0, f"Value: {value if value is not None else 'No value returned'}")
            stdscr.addstr(3, 0, "Press any key to continue...")
            stdscr.getch()

        elif k == ord('s'):
            stdscr.addstr(2, 0, "Enter value to set: ")
            curses.echo()
            input_value = stdscr.getstr(2, 18, 20).decode('utf-8')
            curses.noecho()
            result = call_rpc_function(hosts, SET_FUNCTION, input_value)
            stdscr.addstr(3, 0, f"Set result: {result if result is not None else 'No result returned'}")
            stdscr.addstr(4, 0, "Press any key to continue...")
            stdscr.getch()

        elif k == ord('q'):
            break

        stdscr.refresh()

def main():
    curses.wrapper(tui)


if __name__ == "__main__":
    main()

