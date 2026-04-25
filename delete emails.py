import win32com.client

INBOX_LIMIT = 1000
# Add the email addresses you want to delete here
SENDERS_TO_DELETE = [
    "ubereats@uber.com",
    "noreply@info.wise.com",
    "no-reply@patreon.com",
    "close_friend_updates@facebookmail.com",
    "info@email.meetup.com",
    "info@connectbern.ch",
    "jobnotification@mt.avature.net",
    "newsletter@update.just-eat.ch",
    "noreply@steampowered.com",
    "bingo@patreon.com",
    "info@meetup.com",
    "no-reply@bildirim.mhrs.gov.tr",
    "info@youngpianoseries.ch",
    "garanti@info.garantibbva.com.tr",
    "events@deeplearning.ai",
    "noreply@gmnet.groupemutuel.ch",
    "sbbclient@order.info.sbb.ch",
    "info@meisterzyklus.ch",
    "ubereats@uber.com",
    "noreply@github.com",
    
]


def main():
    senders_set = {addr.lower() for addr in SENDERS_TO_DELETE}
    print("Connecting to Outlook...")
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    inbox = namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
    messages = inbox.Items
    messages.Sort("[ReceivedTime]", True)  # newest first
    to_delete = []
    count = 0
    for msg in messages:
        if count >= INBOX_LIMIT:
            break
        try:
            if msg.SenderEmailAddress.lower() in senders_set:
                to_delete.append(msg)
        except Exception:
            pass
        count += 1
    print(f"Found {len(to_delete)} email(s) from {len(senders_set)} sender(s) to delete.")
    if not to_delete:
        print("Nothing to delete.")
        return

    print("\nEmails to be deleted:")
    for i, msg in enumerate(to_delete, 1):
        try:
            subject = msg.Subject or "(No Subject)"
        except Exception:
            subject = "(Unable to read subject)"
        print(f"  {i}. {subject}")
    print()

    confirm = input(f"Move {len(to_delete)} email(s) to Deleted Items? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return
    # Iterate in reverse to avoid index shifting during deletion
    deleted = 0
    errors = 0
    for msg in reversed(to_delete):
        try:
            msg.Delete()
            deleted += 1
        except Exception as e:
            print(f"  Error: {e}")
            errors += 1
    print(f"\nDone. {deleted} deleted, {errors} errors.")
if __name__ == "__main__":
    main()