import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk  # for image resizing
import cterasdk.settings
from cterasdk import Edge

# Disable TLS/SSL verification (useful for self-signed certificates)
cterasdk.settings.sessions.management.ssl = False


def toggle_ad_user():
    if is_ad_user_var.get():
        ad_user_entry.config(state=tk.NORMAL)
        ad_user_perm_dropdown.config(state="readonly")
    else:
        ad_user_entry.config(state=tk.DISABLED)
        ad_user_perm_dropdown.config(state=tk.DISABLED)

def toggle_ad_group():
    if is_ad_group_var.get():
        ad_group_entry.config(state=tk.NORMAL)
        ad_group_perm_dropdown.config(state="readonly")
    else:
        ad_group_entry.config(state=tk.DISABLED)
        ad_group_perm_dropdown.config(state=tk.DISABLED)


def toggle_nfs():
    if is_nfs_var.get():
        nfsrange_entry.config(state=tk.NORMAL)
        nfsmask_entry.config(state=tk.NORMAL)
        nfsperm_dropdown.config(state="readonly")
    else:
        nfsrange_entry.config(state=tk.DISABLED)
        nfsmask_entry.config(state=tk.DISABLED)
        nfsperm_dropdown.config(state=tk.DISABLED)


def run_flow():
    # Clear previous output
    output_text.delete("1.0", tk.END)

    # Retrieve fixed inputs from the GUI fields
    filer = filer_entry.get().strip()
    adminuser = adminuser_entry.get().strip()
    adminpassword = adminpassword_entry.get().strip()
    base_path = base_folder_entry.get().strip()
    share_name = new_folder_entry.get().strip()

    # For AD User section: only get values if enabled
    if is_ad_user_var.get():
        ad_user = ad_user_entry.get().strip()
        ad_user_perm = ad_user_perm_var.get()
    else:
        ad_user = ""
        ad_user_perm = ""

    # For AD Group section: only get values if enabled
    if is_ad_group_var.get():
        ad_group = ad_group_entry.get().strip()
        ad_group_perm = ad_group_perm_var.get()
    else:
        ad_group = ""
        ad_group_perm = ""

    # For NFS section: only get values if enabled
    if is_nfs_var.get():
        nfsrange = nfsrange_entry.get().strip()
        nfsmask = nfsmask_entry.get().strip()
        nfsperm = nfsperm_var.get()
    else:
        nfsrange = ""
        nfsmask = ""
        nfsperm = ""

    # Retrieve checkbox values (boolean)
    isaduser = is_ad_user_var.get()
    isadgroup = is_ad_group_var.get()
    isnfs = is_nfs_var.get()

    output_text.insert(tk.END, f"Checkbox states - isaduser: {isaduser}, isadgroup: {isadgroup}, isnfs: {isnfs}\n")

    # Construct the full cloud folder path
    full_cloud_folder = f"{base_path.rstrip('/')}/{share_name}"

    try:
        with Edge(filer) as edge:
            # Login to the Edge Filer
            edge.login(adminuser, adminpassword)
            output_text.insert(tk.END, f"Logged in to the Edge Filer at {filer}\n")

            # --- Folder Creation ---
            try:
                edge.files.mkdir(full_cloud_folder)
                output_text.insert(tk.END, f"Folder '{full_cloud_folder}' created successfully.\n")
            except Exception as e:
                output_text.insert(tk.END, f"Error creating folder '{full_cloud_folder}': {e}\n")
                return

            # --- Share Creation ---
            # Prepare NFS permissions (only if NFS enabled)
            if isnfs:
                nfs_client_RW = cterasdk.edge.types.NFSv3AccessControlEntry(nfsrange, nfsmask,
                                                                            cterasdk.edge.enum.FileAccessMode.RW)
                nfs_client_RO = cterasdk.edge.types.NFSv3AccessControlEntry(nfsrange, nfsmask,
                                                                            cterasdk.edge.enum.FileAccessMode.RO)
                nfsclient = nfs_client_RW if nfsperm.upper() == 'RW' else nfs_client_RO
                trusted_nfs_clients = [nfsclient]
            else:
                trusted_nfs_clients = []

            # Prepare AD group permissions (only if AD group enabled)
            if isadgroup:
                domaingroupro = cterasdk.edge.types.ShareAccessControlEntry(cterasdk.edge.enum.PrincipalType.DG,
                                                                            ad_group,
                                                                            cterasdk.edge.enum.FileAccessMode.RO)
                domaingrouprw = cterasdk.edge.types.ShareAccessControlEntry(cterasdk.edge.enum.PrincipalType.DG,
                                                                            ad_group,
                                                                            cterasdk.edge.enum.FileAccessMode.RW)
                domaingroup = domaingrouprw if ad_group_perm.upper() == 'RW' else domaingroupro
            else:
                domaingroup = None

            # Prepare AD user permissions (only if AD user enabled)
            if isaduser:
                domainuserro = cterasdk.edge.types.ShareAccessControlEntry(cterasdk.edge.enum.PrincipalType.DU,
                                                                           ad_user,
                                                                           cterasdk.edge.enum.FileAccessMode.RO)
                domainuserrw = cterasdk.edge.types.ShareAccessControlEntry(cterasdk.edge.enum.PrincipalType.DU,
                                                                           ad_user,
                                                                           cterasdk.edge.enum.FileAccessMode.RW)
                domainuser = domainuserrw if ad_user_perm.upper() == 'RW' else domainuserro
            else:
                domainuser = None

            # Build ACL list only with entries that are enabled
            acl_list = []
            if domaingroup is not None:
                acl_list.append(domaingroup)
            if domainuser is not None:
                acl_list.append(domainuser)

            # Create the share
            edge.shares.add(name=share_name,
                            directory=full_cloud_folder,
                            export_to_nfs=bool(trusted_nfs_clients),
                            trusted_nfs_clients=trusted_nfs_clients,
                            acl=acl_list)
            output_text.insert(tk.END, "Share created successfully.\n")
    except Exception as e:
        output_text.insert(tk.END, f"Error: {e}\n")


# Create the main window
root = tk.Tk()
root.title("CTERA SDK Share Management")

# --- Resize the image to 10% of its original size ---
original_logo = Image.open("217437.png")  # Update filename/path if needed
width, height = original_logo.size
new_width = width // 10
new_height = height // 10
resized_logo = original_logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
logo_image = ImageTk.PhotoImage(resized_logo)

row = 0
# Display the resized logo at the top, spanning two columns
logo_label = tk.Label(root, image=logo_image)
logo_label.grid(row=row, column=0, columnspan=2, padx=5, pady=5)
row += 1

tk.Label(root, text="Filer Address:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
filer_entry = tk.Entry(root, width=50)
filer_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

tk.Label(root, text="Admin User:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
adminuser_entry = tk.Entry(root, width=50)
adminuser_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

tk.Label(root, text="Admin User Password:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
adminpassword_entry = tk.Entry(root, width=50, show="*")
adminpassword_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

tk.Label(root, text="Base Path (e.g. cloud/users/Service Account/data1):").grid(row=row, column=0, sticky=tk.W, padx=5,
                                                                                pady=5)
base_folder_entry = tk.Entry(root, width=50)
base_folder_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

tk.Label(root, text="Share Name:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
new_folder_entry = tk.Entry(root, width=50)
new_folder_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

# AD User Section: Checkbox first, then input fields
is_ad_user_var = tk.BooleanVar(value=False)
ad_user_checkbox = tk.Checkbutton(root, text="Add AD User Permissions", variable=is_ad_user_var, command=toggle_ad_user)
ad_user_checkbox.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
row += 1

tk.Label(root, text="AD User (user@domain.com):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
ad_user_entry = tk.Entry(root, width=50, state=tk.DISABLED)
ad_user_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

tk.Label(root, text="AD User Permission:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
ad_user_perm_var = tk.StringVar(value="RO")
ad_user_perm_dropdown = ttk.Combobox(root, textvariable=ad_user_perm_var, values=["RW", "RO"], state=tk.DISABLED)
ad_user_perm_dropdown.grid(row=row, column=1, padx=5, pady=5)
row += 1

# AD Group Section: Checkbox first, then input fields
is_ad_group_var = tk.BooleanVar(value=False)
ad_group_checkbox = tk.Checkbutton(root, text="Add AD Group Permissions", variable=is_ad_group_var,
                                   command=toggle_ad_group)
ad_group_checkbox.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
row += 1

tk.Label(root, text="AD Group (DOMAIN\\group):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
ad_group_entry = tk.Entry(root, width=50, state=tk.DISABLED)
ad_group_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

tk.Label(root, text="AD Group Permission:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
ad_group_perm_var = tk.StringVar(value="RO")
ad_group_perm_dropdown = ttk.Combobox(root, textvariable=ad_group_perm_var, values=["RW", "RO"], state=tk.DISABLED)
ad_group_perm_dropdown.grid(row=row, column=1, padx=5, pady=5)
row += 1

# NFS Section: Checkbox first, then input fields
is_nfs_var = tk.BooleanVar(value=False)
nfs_checkbox = tk.Checkbutton(root, text="Add NFS Permissions", variable=is_nfs_var, command=toggle_nfs)
nfs_checkbox.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
row += 1

tk.Label(root, text="NFS Range (IP):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
nfsrange_entry = tk.Entry(root, width=50, state=tk.DISABLED)
nfsrange_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

tk.Label(root, text="NFS Net Mask (e.g. 255.255.255.0):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
nfsmask_entry = tk.Entry(root, width=50, state=tk.DISABLED)
nfsmask_entry.grid(row=row, column=1, padx=5, pady=5)
row += 1

tk.Label(root, text="NFS Permission:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
nfsperm_var = tk.StringVar(value="RO")
nfsperm_dropdown = ttk.Combobox(root, textvariable=nfsperm_var, values=["RW", "RO"], state=tk.DISABLED)
nfsperm_dropdown.grid(row=row, column=1, padx=5, pady=5)
row += 1

# Button to trigger the flow
run_button = tk.Button(root, text="Run Flow", command=run_flow)
run_button.grid(row=row, column=0, columnspan=2, pady=10)
row += 1

# Text widget to display output messages
output_text = tk.Text(root, width=80, height=10)
output_text.grid(row=row, column=0, columnspan=2, padx=5, pady=5)

root.mainloop()
