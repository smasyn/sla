// 1404 delete
//const hamburger = document.querySelector('.hamburger');
//const nav = document.querySelector('nav');
//
//hamburger.addEventListener('click', () => {
//    nav.classList.toggle('active');
//});

document.getElementById('contactform').addEventListener('submit', function(event) {
    event.preventDefault();  // Prevent the form from submitting normally

    const data = {
        post_type      : "CONTACT",
        message        : document.getElementById('message').value,
        conversation_id: document.getElementById('email').value,
        project_id     : "none",

    };

    fetch('http://44.232.149.56', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),  // Convert form data to JSON
    })
    .then(response => response.json())
    .then(responseData => console.log(responseData))
    .catch(error => console.error('Error:', error));
  });
