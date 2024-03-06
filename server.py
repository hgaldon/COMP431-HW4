# I abide by the honor code, Harry Galdon

import logging
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
    start_server(port)

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (socket.gethostname(), port)
    server_socket.bind(server_address)
    server_socket.listen(5)

    while True:
        (client_socket, address) = server_socket.accept()
        handle_client(client_socket)

def handle_client(client_socket):
    try:
        client_socket.sendall(f"220 {socket.gethostname()}\n".encode())

        while True:
            command = receive_command(client_socket)
            if command.startswith("HELO"):
                client_domain = command[5:].strip()
                response = f"250 Hello {client_domain}, pleased to meet you\n"
                client_socket.sendall(response.encode())
                start_parse(client_socket)
            elif command.strip() == "QUIT":
                client_socket.sendall(f"221 {socket.gethostname()} closing connection\n".encode())
                break
            else:
                client_socket.sendall("500 Syntax error: command unrecognized\n".encode())
    finally:
        client_socket.close()

def receive_command(client_socket):
    try:
        command = client_socket.recv(1024).decode()
        logging.info(f"Command received: {command}")
        return command.strip()
    except Exception as e:
        logging.error(f"Error receiving command: {e}")
        
def handle_quit(client_socket):
    closing_message = "221 Service closing transmission channel\r\n"
    client_socket.send(closing_message.encode())
    client_socket.close()
    logging.info("Connection closed with client.")


def start_parse(client_socket):
    str_flag = "M"
    mail_list = []

    while True:
        command = receive_command(client_socket)
        if command == "QUIT":
            break
        input_line = command
        if not input_line or input_line == "\n":
            break
        
        str_flag, should_continue = process_input(input_line, str_flag, mail_list, client_socket)
        if not should_continue or str_flag == 'D':
            str_flag = "M"
            mail_list = []

def process_input(input, str_flag, mail_list, socket):
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
            socket.sendall(f"{accepted}\n".encode())
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
            socket.sendall(f"{accepted}\n".encode())
        else:
            return str_flag, False

    elif display == "DATA":
        if str_flag != "R+":
            print(seq)
            return str_flag, False
        socket.sendall(f"{mail_input}\n".encode())
        result = is_valid_data(receive_command(socket))
        if result is not None:
            mail_list.extend(result)
            socket.sendall(f"{accepted}\n".encode())
            saveMail(mail_list)
        else:
            return str_flag, False
        str_flag = "D"

    else:
        print(rej_com)
        return str_flag, False

    return str_flag, True

def receive_command_from_message(message_lines, current_line):
    if current_line < len(message_lines):
        return message_lines[current_line] + '\n'
    return None

def is_valid_data(email_message):
    body = []
    nlFlag = 0
    message_lines = email_message.split('\n')
    current_line = 0
    
    while True:
        message = receive_command_from_message(message_lines, current_line)
        current_line += 1
        
        if message is None:
            break
        
        if message == ".\n" and nlFlag == 1:
            #print(message.strip('\n'))
            #print("Accepted")
            body.append(message)
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
        #print(accepted)
        return accepted

def saveMail(email_list):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        forward_dir = os.path.join(script_dir, 'forward')
        os.makedirs(forward_dir, exist_ok=True)

        email_content = []
        domains = set()

        for line in email_list:
            if line.startswith("From:"):
                email_content = [line]
            elif line == ".\n":
                continue
            else:
                email_content.append(line)
                if line.startswith("To:"):
                    email_addresses = line.split(':')[1].strip().split(',')
                    for email_address in email_addresses:
                        email_address = email_address.strip().strip("<>")
                        domain = email_address.split('@')[-1]
                        domains.add(domain)

        for domain in domains:
            file_path = os.path.join(forward_dir, f"{domain}")
            with open(file_path, "a") as file:
                file.write('\n'.join(email_content) + "\n")
    except IOError as e:
        print(f"Error writing to {file_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()