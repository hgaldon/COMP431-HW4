# I abide by the honor code, Harry Galdon

import sys
import socket


def main():
    if len(sys.argv) != 3:
        print("Usage: python mail_agent.py <hostname> <port>")
        sys.exit(1)

    hostname = sys.argv[1]
    port = int(sys.argv[2])

    from_address, to_addresses, subject, message_lines = prompt_user_for_email()
    send_email_via_smtp(from_address, to_addresses, subject, message_lines, hostname, port)

def is_valid_email(email):
    def is_valid_reverse_path(lp):
        if len(lp) < 1:
            print("ERROR -- string")
            return False
        
        special_chars = set('<>()[]\\.,;:@" \t')
        for i, char in enumerate(lp):
            if char in special_chars:
                if i == 0:
                    print("ERROR -- string")
                    return False
                elif char == '@' and i != 0:
                    return is_valid_domain(lp.split('@', 1)[1], 0)
                else:
                    print("ERROR -- mailbox")
                    return False

        print("ERROR -- mailbox")
        return False

    def is_valid_domain(d, dotCount):
        if len(d) < 1 or d[0].isdigit():
            print("ERROR -- element")
            return False

        for i, element in enumerate(d):
            if not (element.isalpha() or element.isdigit()):
                if i == 0:
                    print("ERROR -- element")
                    return False
                elif element == '.':
                    dotCount += 1
                    return is_valid_domain(d[i+1:], dotCount)
                else:
                    print("ERROR -- path")
                    return False
            if i == len(d) - 1:
                return True

        print("ERROR -- path")
        return False

    return is_valid_reverse_path(email)

def prompt_for_valid_emails(prompt_message):
    while True:
        sys.stdout.write(prompt_message)
        emails_input = sys.stdin.readline().strip()
        emails = [email.strip() for email in emails_input.split(',')]

        if all(is_valid_email(email) for email in emails):
            return emails
        else:
            sys.stdout.write("One or more email addresses are invalid. Please try again.\n")

def prompt_user_for_email():
    from_address = prompt_for_valid_emails("From: \n")[0]
    to_addresses = prompt_for_valid_emails("To: \n")
    sys.stdout.write("Subject: \n")
    subject = sys.stdin.readline().strip()
    
    sys.stdout.write("Message: \n")
    sys.stdout.flush()
    message_lines = []
    while True:
        line = sys.stdin.readline()
        if line.strip() == ".":
            break
        message_lines.append(line.rstrip('\n'))
    
    #print(from_address)
    #print(to_addresses)
    #print(subject)
    #print(message_lines)    
    return from_address, to_addresses, subject, message_lines

def send_email_via_smtp(from_address, to_addresses, subject, message_lines, hostname, port):
    try:
        print("Starting to send email...")
        sock = socket.socket()
        print(f"Connecting to {hostname} on port {port}...")
        
        sock.connect((hostname, port))
        print("Connected.")
        
        server_greeting = sock.recv(1024).decode()
        print(f"Server greeting: {server_greeting}")
        if not server_greeting.startswith('220'):
            print("Failed to receive a valid server greeting.")
            return
        
        helo_command = f"HELO {socket.gethostname()}\n"
        print(f"Sending HELO command: {helo_command.strip()}")
        sock.send(helo_command.encode())
        
        helo_response = sock.recv(1024).decode()
        print(f"HELO response: {helo_response}")
        if not helo_response.startswith('250'):
            print("HELO command failed.")
            return False
        
        mail_from_cmd = f"MAIL FROM: <{from_address}>\n"
        print(f"Sending MAIL FROM command: {mail_from_cmd.strip()}")
        sock.send(mail_from_cmd.encode())
        mail_from_response = sock.recv(1024).decode()
        print(f"MAIL FROM response: {mail_from_response}")
        if not mail_from_response.startswith('250'):
            print("MAIL FROM command failed.")
            return False
        
        for addr in to_addresses:
            rcpt_to_cmd = f"RCPT TO: <{addr}>\n"
            print(f"Sending RCPT TO command for {addr}: {rcpt_to_cmd.strip()}")
            sock.send(rcpt_to_cmd.encode())
            rcpt_to_response = sock.recv(1024).decode()
            print(f"RCPT TO response for {addr}: {rcpt_to_response}")
            if not rcpt_to_response.startswith('250'):
                print(f"RCPT TO command failed for {addr}.")
                return False
        
        print("Sending DATA command.")
        sock.send("DATA\n".encode())
        data_response = sock.recv(1024).decode()
        print(f"DATA response: {data_response}")
        if not data_response.startswith('354'):
            print("DATA command failed.")
            return False
        
        email_message = format_email_message(from_address, to_addresses, subject, message_lines)
        print("Sending email data...")
        sock.send(email_message.encode())
        
        end_data_response = sock.recv(1024).decode()
        print(f"End of data response: {end_data_response}")
        if not end_data_response.startswith('250'):
            print("Error sending email data.")
            return False

        print("Sending QUIT command.")
        sock.send("QUIT".encode())
        quit_response = sock.recv(1024).decode()
        print(f"QUIT response: {quit_response}")
        if not quit_response.startswith('221'):
            print("Error during QUIT.")
            return False

    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    print("Email sent successfully.")
    return True

def format_email_message(from_address, to_addresses, subject, message_lines):
    to_addresses_formatted = ", ".join([f"<{addr}>" for addr in to_addresses])
    headers = [
        f"From: <{from_address}>",
        f"To: {to_addresses_formatted}",
        f"Subject: {subject}",
        "",
    ]
    # Adjust line endings to \n for the email body
    return "\n".join(headers + message_lines) + "\n.\n"

if __name__ == "__main__":
    main()
