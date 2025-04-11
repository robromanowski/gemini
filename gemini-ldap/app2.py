import os
from flask import Flask, render_template, request, flash
import ldap
import ldap.filter # For escaping filter characters

# --- Configuration ---
# Load configuration securely from environment variables
AD_SERVER = os.environ.get('AD_SERVER')
# For python-ldap, port is usually part of the URI, but we might still need it separately
AD_PORT = os.environ.get('AD_PORT', '389') # Defaulting to LDAP port 389 for now
AD_BIND_USER = os.environ.get('AD_BIND_USER') # DN of user to bind as (e.g., rr83008e's DN)
AD_BIND_PASSWORD = os.environ.get('AD_BIND_PASSWORD') # Password for AD_BIND_USER
AD_SEARCH_BASE = os.environ.get('AD_SEARCH_BASE') # e.g., DC=yourdomain,DC=com

# Determine LDAP URI based on port (simple approach for now)
# Assuming port 636 means LDAPS, otherwise LDAP
if AD_PORT == '636':
    LDAP_URI = f"ldaps://{AD_SERVER}:{AD_PORT}"
    print(f"Configured for LDAPS: {LDAP_URI}")
else:
    LDAP_URI = f"ldap://{AD_SERVER}:{AD_PORT}"
    print(f"Configured for LDAP: {LDAP_URI}")
    print("Warning: Using unencrypted LDAP. Credentials and data sent in plain text.")


# Basic validation of configuration
if not all([AD_SERVER, AD_BIND_USER, AD_BIND_PASSWORD, AD_SEARCH_BASE]):
    raise ValueError("Missing required AD configuration environment variables (AD_SERVER, AD_BIND_USER, AD_BIND_PASSWORD, AD_SEARCH_BASE).")

app = Flask(__name__)
# Required for flashing messages
app.secret_key = os.urandom(24)

def get_ad_groups(username):
    """
    Connects to AD using python-ldap and retrieves direct group memberships.
    """
    groups = []
    user_cn = username # Default display name
    conn = None # Initialize connection object

    try:
        # 1. Initialize connection
        print(f"Initializing LDAP connection to {LDAP_URI}...")
        conn = ldap.initialize(LDAP_URI)

        # Set options
        conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        # Disable chasing referrals automatically, often needed for AD
        conn.set_option(ldap.OPT_REFERRALS, 0)

        # --- TLS Options (If using LDAPS) ---
        # If you switch back to LDAPS (port 636) later, you might need these.
        # To disable certificate verification for testing (like validate=None in ldap3):
        if LDAP_URI.startswith('ldaps'):
             print("LDAPS detected, disabling certificate verification (OPT_X_TLS_NEVER).")
             conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
             # Alternatively, for proper validation:
             # conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
             # conn.set_option(ldap.OPT_X_TLS_CACERTFILE, '/path/to/your/ca_cert.pem')

        # 2. Bind (Authenticate)
        print(f"Attempting Simple Bind as {AD_BIND_USER}...")
        # Use simple_bind_s for synchronous operation
        conn.simple_bind_s(AD_BIND_USER, AD_BIND_PASSWORD)
        print(f"Successfully bound to AD as {AD_BIND_USER}")

        # 3. Search for the user
        # Escape the username to prevent LDAP injection
        escaped_username = ldap.filter.escape_filter_chars(username)
        search_filter = f'(&(objectClass=user)(sAMAccountName={escaped_username}))'
        attributes_to_retrieve = ['distinguishedName', 'memberOf', 'cn'] # Attributes we want

        print(f"Searching for user with filter: {search_filter} in base {AD_SEARCH_BASE}")
        # Use search_s for synchronous search
        results = conn.search_s(AD_SEARCH_BASE, ldap.SCOPE_SUBTREE, search_filter, attributes_to_retrieve)
        print(f"Search returned {len(results)} entries.")

        if results:
            # Results is a list of tuples: [(dn, {attr_dict}), ...]
            user_dn, user_attrs = results[0] # Get first result
            print(f"Found user DN: {user_dn}")

            # Get display name if available
            if 'cn' in user_attrs and user_attrs['cn']:
                 # Decode bytes to string
                 user_cn = user_attrs['cn'][0].decode('utf-8', 'ignore')

            # Get group memberships
            if 'memberOf' in user_attrs:
                group_dns_bytes = user_attrs['memberOf']
                print(f"Raw memberOf attribute (bytes): {group_dns_bytes}")
                for group_dn_bytes in group_dns_bytes:
                    try:
                        # Decode bytes to string
                        group_dn = group_dn_bytes.decode('utf-8', 'ignore')
                        # Extract CN= part
                        cn_part = group_dn.split(',')[0]
                        if cn_part.upper().startswith('CN='):
                            groups.append(cn_part[3:])
                        else:
                            groups.append(group_dn) # Fallback
                    except Exception as parse_ex:
                         print(f"Error parsing group DN: {group_dn_bytes}, Error: {parse_ex}")
                         # Attempt to append the decoded string even if parsing fails
                         try:
                             groups.append(group_dn_bytes.decode('utf-8', 'ignore'))
                         except Exception:
                             pass # Ignore if decoding also fails

                groups.sort()
            else:
                 print(f"User {user_cn} has no 'memberOf' attribute.")

        else:
            print(f"User '{username}' not found.")
            raise ValueError(f"User '{username}' not found.") # Raise specific error

    except ldap.INVALID_CREDENTIALS:
        print("LDAP Error: Invalid Credentials!")
        flash(f"Authentication failed: Invalid credentials provided for {AD_BIND_USER}.", "error")
        raise # Re-raise to be caught by the route
    except ldap.SERVER_DOWN as e:
        print(f"LDAP Error: Server Down! Details: {e}")
        flash(f"Could not connect to LDAP server at {LDAP_URI}. Server might be down or unreachable.", "error")
        raise
    except ldap.LDAPError as e:
        # Catch other specific LDAP errors if needed, or general LDAPError
        print(f"An LDAP error occurred: {e}")
        # Try to extract more specific info if possible (depends on error type)
        error_details = str(e)
        try:
            # python-ldap errors often have a dictionary with more info
            if isinstance(e.args, tuple) and len(e.args) > 0 and isinstance(e.args[0], dict):
                error_details = e.args[0].get('desc', str(e))
                if 'info' in e.args[0]:
                    error_details += f" - {e.args[0]['info']}"
        except Exception:
             pass # Ignore if details extraction fails
        flash(f"An LDAP error occurred: {error_details}", "error")
        raise
    except Exception as e:
        # Catch non-LDAP errors
        print(f"An unexpected error occurred: {e}")
        flash(f"An unexpected error occurred: {e}", "error")
        raise
    finally:
        # 4. Unbind connection if it was initialized
        if conn:
            try:
                print("Unbinding LDAP connection.")
                conn.unbind_s()
            except ldap.LDAPError as unbind_ex:
                 print(f"Error during LDAP unbind: {unbind_ex}")

    return user_cn, groups

# --- Flask Route (@app.route('/')) remains largely the same ---
# It catches exceptions raised by get_ad_groups and passes
# groups or error messages to the template.

@app.route('/', methods=['GET', 'POST'])
def index():
    groups = None
    error_message = None
    searched_user = None # Keep track of the user that was searched for
    display_name_on_page = None # Keep track of display name for results header

    if request.method == 'POST':
        username = request.form.get('username')
        searched_user = username # Store for display even if lookup fails
        if username:
            try:
                print(f"--- Initiating search for username: {username} ---")
                # Call the refactored function
                display_name, groups = get_ad_groups(username)
                display_name_on_page = f"{display_name} ({username})" # Update with display name if found

                if not groups:
                     # Check if user was actually found (groups is [] vs exception)
                     if display_name: # Check if display_name was returned (implies user found)
                          flash(f"User '{display_name_on_page}' found, but is not a direct member of any groups.", "warning")
                     # Else: user not found error handled by exception

                print(f"--- Search complete for {username}. Groups found: {len(groups) if groups is not None else 'Error'} ---")
            except ValueError as e: # Catch specific "user not found" error from get_ad_groups
                error_message = str(e)
                # Flash message might be set already for LDAP errors, avoid double flashing
                if not any(category == 'error' for category, _ in app.jinja_env.globals['get_flashed_messages'](with_categories=True)):
                    flash(error_message, "error")
                print(f"--- Search failed for {username}: {error_message} ---")
            except Exception as e: # Catch other errors raised from get_ad_groups (LDAPError etc)
                # Flash message should already be set within get_ad_groups for LDAP errors
                if not any(category == 'error' for category, _ in app.jinja_env.globals['get_flashed_messages'](with_categories=True)):
                    flash(f"An unexpected error occurred processing the request for '{username}'. Check logs.", "error")
                print(f"--- Search failed for {username} due to caught exception: {e} ---")
        else:
            error_message = "Please enter a username."
            flash(error_message, "warning")

    # Render the template, passing the results (or None)
    # Ensure display_name_on_page is passed for the results header
    return render_template('index.html', groups=groups, error_message=error_message, searched_user=display_name_on_page or searched_user, username_value=request.form.get('username', ''))


if __name__ == '__main__':
    # Make sure debug=False for production
    app.run(debug=True, host='0.0.0.0', port=5000)
