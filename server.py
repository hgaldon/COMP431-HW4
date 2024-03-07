# I abide by the honor code, Harry Galdon

import logging
import socket
import threading
import sys
import os

class SMTPResponses:
    accepted = "250 OK"
    rej_com = "500 Syntax error: command unrecognized"
    rej_param = "501 Syntax error in parameters or arguments"
    mail_input = "354 Start mail input; end with <CRLF>.<CRLF>"
    seq = "503 Bad sequence of commands"

def main():
    if len(sys.argv) != 2:
        print("Usage: python SMTP1.py <port>")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Port number must be an integer")
        sys.exit(1)

    if port < 1 or port > 65535:
        print("Port number must be between 1 and 65535")
        sys.exit(1)

    if not start_server(port):
        print("Failed to start the server after multiple attempts.")
        sys.exit(1)

def start_server(initial_port, max_attempts=5):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    for attempt in range(max_attempts):
        try:
            port = initial_port + attempt
            server_address = (socket.gethostname(), port)
            server_socket.bind(server_address)
            server_socket.listen(5)
            while True:
                client_socket, address = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(client_socket,))
                client_thread.start()
            return True
        except OSError as e:
            if e.errno == socket.errno.EADDRINUSE:
                print(f"Port {port} is in use, trying the next port...")
            else:
                print(f"Failed to start server: {e}")
                break
    return False

def handle_client(client_socket):
    try:
        client_socket.sendall(f"220 {socket.gethostname()}\n".encode())
        while True:
            command = receive_command(client_socket)
            if command.startswith("HELO"):
                s = command[4:]
                if s[0] != ' ' or s[0] != '\t':
                    client_socket.sendall((SMTPResponses.rej_com + "\n").encode())
                    break
                s = s.lstrip()
                index = len(s)
                newlineFirstBool = False
                for i, char in enumerate(s):
                    if char in ('\n'):
                        newlineFirstBool = True
                        index = i
                        break
                    elif char in (' ', '\t'):
                        index = i
                        break
                if index == len(s):
                    client_socket.sendall((SMTPResponses.rej_com + "\n").encode())
                    break
                elif not newlineFirstBool:
                    client_domain = s[:index]
                    s = s[index:].lstrip()
                    if not s.startswith('\n') or not s.endswith('\n'):
                        client_socket.sendall((SMTPResponses.rej_com + "\n").encode())
                        break
                else:
                    s = s.split('\n', 1)
                    client_domain = s[0]
                    s = s[1]
                    if len(s) > 0:
                        client_socket.sendall((SMTPResponses.rej_com + "\n").encode())
                        break
                response = f"250 Hello {client_domain}, pleased to meet you\n"
                client_socket.sendall(response.encode())
                start_parse(client_socket)
                break
            elif command.strip() == "QUIT":
                handle_quit(client_socket)
                break
            else:
                client_socket.sendall((SMTPResponses.rej_com + "\n").encode())
    except Exception as e:
        logging.error(f"Error handling client: {e}")
    finally:
        client_socket.close()
        logging.info("Connection closed with client.")

def receive_command(client_socket):
    try:
        command = client_socket.recv(1024).decode()
        logging.info(f"Command received: {command}")
        return command
    except Exception as e:
        logging.error(f"Error receiving command: {e}")
        
def handle_quit(client_socket):
    client_socket.sendall(f"221 {socket.gethostname()} closing connection\n".encode())

def start_parse(client_socket):
    str_flag = "M"
    mail_list = []

    while True:
        command = receive_command(client_socket)
        if command.strip() == "QUIT":
            handle_quit(client_socket)
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
        s = input[4:]
        if s[0] != ' ' or s[0] != '\t':
            print(SMTPResponses.rej_com)
            return str_flag, False
        s = s.lstrip()
        if not s.startswith("TO:"):
            print(SMTPResponses.rej_com)
            return str_flag, False
        if str_flag != "R" and str_flag != "R+":
            print(SMTPResponses.seq) 
            return str_flag, False
        result = is_valid_rcpt_to(s)
        if result == SMTPResponses.accepted:
            to_addr = display.split(maxsplit=1)[1]
            mail_list.append(to_addr)
            str_flag = "R+"
            socket.sendall(f"{result}\n".encode())
        else:
            return str_flag, False

    elif input.startswith("MAIL"):
        s = input[4:]
        if s[0] != ' ' or s[0] != '\t':
            print(SMTPResponses.rej_com)
            return str_flag, False
        s = s.lstrip()
        if not s.startswith("FROM:"):
            print(SMTPResponses.rej_com)
            return str_flag, False
        if str_flag != "M":
            print(SMTPResponses.seq)
            return str_flag, False
        result = is_valid_mail_from_cmd(s)
        if result == SMTPResponses.accepted:
            from_addr = display.split(maxsplit=1)[1]
            mail_list.append(from_addr)
            str_flag = "R"
            socket.sendall(f"{result}\n".encode())
        else:
            return str_flag, False

    elif display == "DATA":
        if str_flag != "R+":
            print(SMTPResponses.seq)
            return str_flag, False
        socket.sendall(f"{SMTPResponses.mail_input}\n".encode())
        result = is_valid_data(receive_command(socket))
        if result is not None:
            mail_list.extend(result)
            socket.sendall(f"{SMTPResponses.accepted}\n".encode())
            saveMail(mail_list)
        else:
            return str_flag, False
        str_flag = "D"

    else:
        print(SMTPResponses.rej_com)
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
                    print(SMTPResponses.rej_com)
                else:
                    print(SMTPResponses.rej_param)
                return

def is_valid_rcpt_to(s):
    path = s.split(':', 1)[1]
    path = path.lstrip()
    if not path[0] == '<' and path[1] == '<':
        print(SMTPResponses.rej_com)
        return

    if not path.startswith("<"):
        print(SMTPResponses.rej_param)
        return

    return is_valid_reverse_path(path[1:])

def is_valid_mail_from_cmd(s):
    path = s.split(':', 1)[1]
    path = path.lstrip()
    if not path[0] == '<' and path[1] == '<':
        print(SMTPResponses.rej_com)
        return

    if not path.startswith("<"):
        print(SMTPResponses.rej_param)
        return

    return is_valid_reverse_path(path[1:])

def is_valid_reverse_path(lp):
    if len(lp) < 1:
        print(SMTPResponses.rej_param)
        return
    
    special_chars = set('<>()[]\\.,;:@" \t')
    for i, char in enumerate(lp):
        if char in special_chars:
            if i == 0:
                print(SMTPResponses.rej_param)
                return
            elif char == '@' and i != 0:
                return is_valid_domain(lp.split('@', 1)[1], 0)
            else:
                print(SMTPResponses.rej_param)
                return

    print(SMTPResponses.rej_param)
    return

def is_valid_domain(d, dotCount):
    if len(d) < 1 or d[0].isdigit():
        print(SMTPResponses.rej_param)
        return

    for i, element in enumerate(d):
        if not (element.isalpha() or element.isdigit()):
            if i == 0:
                print(SMTPResponses.rej_param)
                return
            elif element == '>':
                return is_valid(d[i+1:])
            elif element == '.':
                dotCount += 1
                return is_valid_domain(d[i+1:], dotCount)
            else:
                print(SMTPResponses.rej_param)
                return

    print(SMTPResponses.rej_param)
    return

def is_valid(s):
    s = s.lstrip(' \t')
    if not s.startswith('\n') or not s.endswith('\n'):
        print(SMTPResponses.rej_com)
        return
    else:
        return SMTPResponses.accepted

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