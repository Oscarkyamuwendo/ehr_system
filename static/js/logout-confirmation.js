function confirmLogout(event) {
    event.preventDefault(); // Prevents the default link action
    if (confirm("Are you sure you want to log out?")) {
        window.location.href = event.target.href; // Redirect to logout URL if confirmed
    }
}
