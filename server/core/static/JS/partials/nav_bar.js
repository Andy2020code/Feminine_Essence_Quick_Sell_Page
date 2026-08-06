document.addEventListener("DOMContentLoaded", function toggleMobileMenu(){
    const btn = document.getElementById("mobile_menu_icon");
    const nav = document.querySelector(".nav_links");
    const icon = document.querySelector(".menu_icon");

    if (btn && icon && nav) {
        btn.addEventListener("click", function () {
            icon.classList.add("animate");

            setTimeout(() => {
                const isOpen = nav.classList.toggle("active");

                icon.src = isOpen
                    ? "/static/MEDIA/images/icons/close.png"
                    : "/static/MEDIA/images/icons/line.png";

                icon.classList.remove("animate");
            }, 100);
        });
    }
});
