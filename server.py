# I abide by the honor code, Harry Galdon

import errno
import socket
import sys
import re
import os


accepted = "250 OK"
rej_com = "500 Syntax error: command unrecognized"
rej_param = "501 Syntax error in parameters or arguments"
mail_input = "354 Start mail input; end with <CRLF>.<CRLF>"
seq = "503 Bad sequence of commands"

def main():
    if len(sys.argv) != 2:
    print("Usage: python SMTP1.py <port>")
    sys.exit(1)

    port = int(sys.argv[1])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', port))  # Bind to all interfaces
    server_socket.listen(5)  # Listen for up to 5 connections

    str_flag = "M"
    mail_list = []

    while True:
        input_line = sys.stdin.readline()
        if input_line == '':
            break
        str_flag, should_continue = process_input(input_line, str_flag, mail_list)
        if not should_continue or str_flag == 'D':
            str_flag = "M"
            mail_list = []

def process_input(input, str_flag, mail_list):
    display = input.strip('\n')
    print(display)

    if input.startswith("RCPT"):
        s = input
        s = s.split('T', 1)[1]
        if not bool(re.fullmatch(r'[ \t]+', s[0])):
            print(rej_com)
            return str_flag, False
        s = s.lstrip()
        if not s.startswith("TO:"):
            print(rej_com)
            return str_flag, False
        if str_flag != "R" and str_flag != "R+":
            print(seq) 
            return str_flag, False
        result = is_valid_rcpt_to(s)
        if result == accepted:
            to_addr = display.split(maxsplit=1)[1]
            mail_list.append(to_addr)
            str_flag = "R+"
        else:
            return str_flag, False

    elif input.startswith("MAIL"):
        s = input
        s = s.split('L', 1)[1]
        if not bool(re.fullmatch(r'[ \t]+', s[0])):
            print(rej_com)
            return str_flag, False
        s = s.lstrip()
        if not s.startswith("FROM:"):
            print(rej_com)
            return str_flag, False
        if str_flag != "M":
            print(seq)
            return str_flag, False
        result = is_valid_mail_from_cmd(s)
        if result == accepted:
            from_addr = display.split(maxsplit=1)[1]
            mail_list.append(from_addr)
            str_flag = "R"
        else:
            return str_flag, False

    elif display == "DATA":
        if str_flag != "R+":
            print(seq)
            return str_flag, False
        result = is_valid_data()
        if result is not None:
            mail_list.extend(result)
            saveMail(mail_list)
        else:
            return str_flag, False
        str_flag = "D"

    else:
        print(rej_com)
        return str_flag, False

    return str_flag, True
        
def is_valid_data():
    body = []
    nlFlag = 0
    print(mail_input)
    while True:
        message = sys.stdin.readline()
        if message == ".\n" and nlFlag == 1:
            print(message.strip('\n'))
            print(accepted)
            return body  
        else:
            if message.endswith('\n'):
                nlFlag = 1
                msg = message.strip('\n')
                print(msg)
                body.append(msg)
            else:
                if '\n' in message:
                    print(rej_com)
                else:
                    print(rej_param)
                return

def is_valid_rcpt_to(s):
    path = s.split(':', 1)[1]
    path = path.lstrip()
    if not path[0] == '<' and path[1] == '<':
        print(rej_com)
        return

    if not path.startswith("<"):
        print(rej_param)
        return

    return is_valid_reverse_path(path[1:])

def is_valid_mail_from_cmd(s):
    path = s.split(':', 1)[1]
    path = path.lstrip()
    if not path[0] == '<' and path[1] == '<':
        print(rej_com)
        return

    if not path.startswith("<"):
        print(rej_param)
        return

    return is_valid_reverse_path(path[1:])

def is_valid_reverse_path(lp):
    if len(lp) < 1:
        print(rej_param)
        return
    
    special_chars = set('<>()[]\\.,;:@" \t')
    for i, char in enumerate(lp):
        if char in special_chars:
            if i == 0:
                print(rej_param)
                return
            elif char == '@' and i != 0:
                return is_valid_domain(lp.split('@', 1)[1], 0)
            else:
                print(rej_param)
                return

    print(rej_param)
    return

def is_valid_domain(d, dotCount):
    if len(d) < 1 or d[0].isdigit():
        print(rej_param)
        return

    for i, element in enumerate(d):
        if not (element.isalpha() or element.isdigit()):
            if i == 0:
                print(rej_param)
                return
            elif element == '>':
                return is_valid(d[i+1:])
            elif element == '.':
                dotCount += 1
                return is_valid_domain(d[i+1:], dotCount)
            else:
                print(rej_param)
                return

    print(rej_param)
    return

def is_valid(s):
    s = s.lstrip(' \t')
    if not s.startswith('\n'):
        print(rej_param)
        return
    elif not s.endswith('\n'):
        print(rej_com)
        return
    else:
        print(accepted)
        return accepted

def saveMail(email_list):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        forward_dir = os.path.join(script_dir, 'forward')
        os.makedirs(forward_dir, exist_ok=True)

        from_line = email_list[0].replace("FROM", "From")
        to_email_addresses = []

        for line in email_list[1:]:
            if line.upper().startswith("TO"):
                line = line.replace("TO", "To")
                to_email_addresses.append(line)

        email_content = [from_line] + to_email_addresses
        for line in email_list[1:]:
            if not line.upper().startswith("TO"):
                email_content.append(line)

        for to_line in to_email_addresses:
            start = to_line.find('<')
            end = to_line.find('>')
            email_address = to_line[start + 1:end]

            safe_email_address = "".join(x if x.isalnum() or x in {'@', '.'} else '' for x in email_address)
            file_path = os.path.join(forward_dir, safe_email_address)
            try:
                with open(file_path, "a") as file:
                    file.write('\n'.join(email_content) + "\n")
            except IOError as e:
                if e.errno == errno.EACCES:
                    print(f"Permission denied: {file_path}", file=sys.stderr)
                    sys.exit(1)
                elif e.errno == errno.ENOSPC:
                    print("No space left on device to write: ", file_path, file=sys.stderr)
                    sys.exit(1)
                else:
                    print(f"Error writing to {file_path}: {e}", file=sys.stderr)
                    sys.exit(1)
            except Exception as e:
                print(f"An unexpected error occurred: {e}", file=sys.stderr)
                sys.exit(1)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()