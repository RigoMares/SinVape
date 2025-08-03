// --- REFERENCIAS A ELEMENTOS DEL DOM ---
const authContainer = document.getElementById('auth-container');
const gameContainer = document.getElementById('game-container');
const registerBtn = document.getElementById('register-btn');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const errorMessage = document.getElementById('error-message');

// --- LÓGICA DE AUTENTICACIÓN ---

// Escuchar cambios en el estado de autenticación
auth.onAuthStateChanged(user => {
    if (user) {
        // Usuario está logueado
        console.log('Usuario logueado:', user.email);
        authContainer.classList.add('hidden');
        gameContainer.classList.remove('hidden');
        startGame(); // Iniciar el juego
    } else {
        // Usuario no está logueado
        console.log('No hay usuario logueado.');
        authContainer.classList.remove('hidden');
        gameContainer.classList.add('hidden');
    }
});

// Manejar el registro de un nuevo usuario
registerBtn.addEventListener('click', () => {
    const email = emailInput.value;
    const password = passwordInput.value;

    if (!email || !password) {
        errorMessage.textContent = 'Por favor, introduce correo y contraseña.';
        return;
    }

    auth.createUserWithEmailAndPassword(email, password)
        .then(userCredential => {
            console.log('Usuario registrado:', userCredential.user);
            errorMessage.textContent = ''; // Limpiar errores
        })
        .catch(error => {
            console.error('Error de registro:', error.message);
            errorMessage.textContent = 'Error al registrar: ' + error.message;
        });
});

// Manejar el inicio de sesión
loginBtn.addEventListener('click', () => {
    const email = emailInput.value;
    const password = passwordInput.value;

    if (!email || !password) {
        errorMessage.textContent = 'Por favor, introduce correo y contraseña.';
        return;
    }

    auth.signInWithEmailAndPassword(email, password)
        .then(userCredential => {
            console.log('Usuario inició sesión:', userCredential.user);
            errorMessage.textContent = ''; // Limpiar errores
        })
        .catch(error => {
            console.error('Error de inicio de sesión:', error.message);
            errorMessage.textContent = 'Error al iniciar sesión: ' + error.message;
        });
});

// Manejar el cierre de sesión
logoutBtn.addEventListener('click', () => {
    auth.signOut().then(() => {
        // Cierre de sesión exitoso. El onAuthStateChanged se encargará del resto.
        console.log('Sesión cerrada.');
    }).catch(error => {
        console.error('Error al cerrar sesión:', error);
    });
});


// --- LÓGICA DEL JUEGO ---
// La envolvemos en una función para llamarla solo cuando sea necesario

function startGame() {
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');

    // --- Jugador (VERSIÓN ACTUALIZADA) ---
    const player = {
        x: canvas.width / 2 - 25,
        y: canvas.height - 60,
        width: 50,
        height: 50,
        color: 'green',
        speed: 8,
        dx: 0
    };

    // --- Obstáculos (Cigarros) ---
    let obstacles = [];
    const obstacleWidth = 20;
    const obstacleHeight = 40;
    const obstacleColor = 'red';
    let obstacleSpeed = 2;
    let obstacleSpawnRate = 120;
    let frameCount = 0;

    // --- Controles del Teclado ---
    document.addEventListener('keydown', keyDown);
    document.addEventListener('keyup', keyUp);

    function keyDown(e) {
        if (e.key === 'ArrowRight' || e.key === 'Right') {
            player.dx = player.speed;
        } else if (e.key === 'ArrowLeft' || e.key === 'Left') {
            player.dx = -player.speed;
        }
    }

    function keyUp(e) {
        if (
            e.key === 'ArrowRight' || e.key === 'Right' ||
            e.key === 'ArrowLeft' || e.key === 'Left'
        ) {
            player.dx = 0;
        }
    }

    function drawPlayer() {
        ctx.fillStyle = player.color;
        ctx.fillRect(player.x, player.y, player.width, player.height);
    }

    function drawObstacles() {
        obstacles.forEach(obstacle => {
            ctx.fillStyle = obstacleColor;
            ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height);
        });
    }

    function movePlayer() {
        player.x += player.dx;
        if (player.x < 0) player.x = 0;
        if (player.x + player.width > canvas.width) player.x = canvas.width - player.width;
    }

    function moveObstacles() {
        obstacles.forEach(obstacle => {
            obstacle.y += obstacleSpeed;
        });
        obstacles = obstacles.filter(obstacle => obstacle.y < canvas.height);
    }

    function spawnObstacle() {
        frameCount++;
        if (frameCount % obstacleSpawnRate === 0) {
            const x = Math.random() * (canvas.width - obstacleWidth);
            obstacles.push({ x: x, y: -obstacleHeight });
        }
    }

    function checkCollisions() {
        obstacles.forEach(obstacle => {
            if (
                player.x < obstacle.x + obstacle.width &&
                player.x + player.width > obstacle.x &&
                player.y < obstacle.y + obstacle.height &&
                player.y + player.height > obstacle.y
            ) {
                alert('¡Perdiste! Evita los cigarros.');
                resetGame();
            }
        });
    }

    function resetGame() {
        obstacles = [];
        player.x = canvas.width / 2 - 25;
        frameCount = 0;
    }

    function clearCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    function update() {
        clearCanvas();
        spawnObstacle();
        drawObstacles();
        moveObstacles();
        drawPlayer();
        movePlayer();
        checkCollisions();
        requestAnimationFrame(update);
    }

    // Iniciar el bucle del juego
    update();
}