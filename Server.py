# I abide by the honor code, Harry Galdon

import socket
import sys
import os
import re

class SMTPResponses:
    accepted = "250 OK"
    rej_com = "500 Syntax error: command unrecognized"
    rej_param = "501 Syntax error in parameters or arguments"
    mail_input = "354 Start mail input; end with <CRLF>.<CRLF>"
    seq = "503 Bad sequence of commands"

def main():
    if len(sys.argv) != 2:
        sys.stdout.write("Usage: python Server.py <port>\n")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        sys.stdout.write("Port number must be an integer\n")
        sys.exit(1)

    if port < 1 or port > 65535:
        sys.stdout.write("Port number must be between 1 and 65535\n")
        sys.exit(1)

    if not start_server(port):
        sys.stdout.write("Failed to start the server after multiple attempts\n")
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
                handle_client(client_socket)
            return True
        except OSError as e:
            if e.errno == socket.errno.EADDRINUSE:
                sys.stdout.write(f"Port {port} is in use, trying the next port...\n")
            else:
                sys.stdout.write(f"Failed to start server: {e}\n")
                break
    return False

def handle_client(client_socket):
    error_message = ""
    try:
        client_socket.sendall(f"220 {socket.gethostname()}\n".encode())
        while True:
            command = receive_command(client_socket)
            if not command:
                break
            if command.startswith("HELO"):
                handle_helo(client_socket, command)
                start_parse(client_socket)
                break
            elif command.strip() == "QUIT":
                handle_quit(client_socket)
                break
            else:
                client_socket.sendall(SMTPResponses.rej_com.encode())
    except socket.error as e:
        error_message = f"Socket error occurred: {e}"
    except Exception as e:
        error_message = f"An error occurred: {e}"
    finally:
        client_socket.close()
        if error_message:
            sys.stdout.write(error_message)

def receive_command(client_socket):
    try:
        command = client_socket.recv(1024).decode()
        return command
    except Exception as e:
        sys.stdout.write(f"Error receiving command: {e}")
        
def handle_quit(client_socket):
    client_socket.sendall(f"221 {socket.gethostname()} closing connection\n".encode())

def handle_helo(client_socket, command):
    parts = re.split(r'\s+', command, 1)
    if len(parts) < 2:
        client_socket.sendall(SMTPResponses.rej_com.encode())
    else:
        s = parts[1]
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
            client_socket.sendall(SMTPResponses.rej_com.encode())
        elif not newlineFirstBool:
            client_domain = s[:index]
            s = s[index:].lstrip()
            if not s.startswith('\n') or not s.endswith('\n'):
                client_socket.sendall(SMTPResponses.rej_com.encode())
        else:
            s = s.split('\n', 1)
            client_domain = s[0]
            s = s[1]
            if len(s) > 0:
                client_socket.sendall(SMTPResponses.rej_com.encode())
        response = f"250 Hello {client_domain}, pleased to meet you\n"
        client_socket.sendall(response.encode())

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
    if input.startswith("RCPT"):
        s = input[4:]
        if s[0] != ' ' and s[0] != '\t':
            socket.sendall(SMTPResponses.rej_com.encode())
            return str_flag, False
        s = s.lstrip()
        if not s.startswith("TO:"):
            socket.sendall(SMTPResponses.rej_com.encode())
            return str_flag, False
        if str_flag != "R" and str_flag != "R+":
            socket.sendall(SMTPResponses.seq.encode()) 
            return str_flag, False
        result = is_valid_rcpt_to(s)
        if result == SMTPResponses.accepted:
            to_addr = s.split(maxsplit=1)[1]
            mail_list.append(to_addr)
            str_flag = "R+"
            socket.sendall(f"{result}\n".encode())
        else:
            socket.sendall(f"{result}\n".encode())
            return str_flag, False

    elif input.startswith("MAIL"):
        s = input[4:]
        if s[0] != ' ' and s[0] != '\t':
            socket.sendall(SMTPResponses.rej_com.encode())
            return str_flag, False
        s = s.lstrip()
        if not s.startswith("FROM:"):
            socket.sendall(SMTPResponses.rej_com.encode())
            return str_flag, False
        if str_flag != "M":
            socket.sendall(SMTPResponses.seq.encode())
            return str_flag, False
        result = is_valid_mail_from_cmd(s)
        if result == SMTPResponses.accepted:
            from_addr = s.split(maxsplit=1)[1]
            mail_list.append(from_addr)
            str_flag = "R"
            socket.sendall(f"{result}\n".encode())
        else:
            socket.sendall(f"{result}\n".encode())
            return str_flag, False

    elif input.strip() == "DATA":
        if str_flag != "R+":
            socket.sendall(SMTPResponses.seq.encode())
            return str_flag, False
        socket.sendall(f"{SMTPResponses.mail_input}\n".encode())
        body, result = is_valid_data(receive_command(socket))
        if result == SMTPResponses.accepted:
            mail_list.extend(body)
            socket.sendall(f"{result}\n".encode())
            saveMail(mail_list)
        else:
            socket.sendall(f"{result}\n".encode())
            return str_flag, False
        str_flag = "D"

    else:
        socket.sendall(SMTPResponses.rej_com.encode())
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
        
        if message == ".\n" and nlFlag == 1:
            body.append(message)
            return body, SMTPResponses.accepted
        else:
            if message.endswith('\n'):
                nlFlag = 1
                msg = message.strip('\n')
                body.append(msg)
            else:
                if message is None:
                    return body, SMTPResponses.rej_param
                if '\n' in message:
                    return None, SMTPResponses.rej_com
                else:
                    return None, SMTPResponses.rej_param

def is_valid_rcpt_to(s):
    path = s.split(':', 1)[1]
    path = path.lstrip()
    if not path[0] == '<' and path[1] == '<':
        return SMTPResponses.rej_com

    if not path.startswith("<"):
        return SMTPResponses.rej_param

    return is_valid_reverse_path(path[1:])

def is_valid_mail_from_cmd(s):
    path = s.split(':', 1)[1]
    path = path.lstrip()
    if not path[0] == '<' and path[1] == '<':
        return SMTPResponses.rej_com

    if not path.startswith("<"):
        return SMTPResponses.rej_param

    return is_valid_reverse_path(path[1:])

def is_valid_reverse_path(lp):
    if len(lp) < 1:
        return SMTPResponses.rej_param
    
    special_chars = set('<>()[]\\.,;:@" \t')
    for i, char in enumerate(lp):
        if char in special_chars:
            if i == 0:
                return SMTPResponses.rej_param
            elif char == '@' and i != 0:
                return is_valid_domain(lp.split('@', 1)[1], 0)
            else:
                return SMTPResponses.rej_param

    return SMTPResponses.rej_param

def is_valid_domain(d, dotCount):
    if len(d) < 1 or d[0].isdigit():
        return SMTPResponses.rej_param

    for i, element in enumerate(d):
        if not (element.isalpha() or element.isdigit()):
            if i == 0:
                return SMTPResponses.rej_param
            elif element == '>':
                return is_valid(d[i+1:])
            elif element == '.':
                dotCount += 1
                return is_valid_domain(d[i+1:], dotCount)
            else:
                return SMTPResponses.rej_param

    return SMTPResponses.rej_param

def is_valid(s):
    s = s.lstrip(' \t')
    if not s.startswith('\n') and not s.endswith('\n'):
        return SMTPResponses.rej_com
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
        sys.stdout.write(f"Error writing to {file_path}: {e}\n")
    except Exception as e:
        sys.stdout.write(f"An unexpected error occurred: {e}\n")

if __name__ == "__main__":
    main()