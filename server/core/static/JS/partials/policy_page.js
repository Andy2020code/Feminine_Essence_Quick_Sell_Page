function toggleDropdown(id, button) {
    const dropdown = document.getElementById(id);
    
    dropdown.classList.toggle("active_dropdown");
    button.classList.toggle("active_dropdown_icon_anim");
}