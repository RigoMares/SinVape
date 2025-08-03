// --- Configuración Inicial ---
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// --- Jugador ---
const player = {
  x: canvas.width / 2 - 25, // Centrado horizontalmente
  y: canvas.height - 60,    // En la parte inferior
  width: 50,
  height: 50,
  color: 'blue',
  speed: 5,
  dx: 0 // Dirección del movimiento horizontal
};

// --- Obstáculos (Cigarros) ---
let obstacles = [];
const obstacleWidth = 20;
const obstacleHeight = 40;
const obstacleColor = 'red';
let obstacleSpeed = 2;
let obstacleSpawnRate = 120; // Aproximadamente cada 2 segundos
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
    e.key === 'ArrowRight' ||
    e.key === 'Right' ||
    e.key === 'ArrowLeft' ||
    e.key === 'Left'
  ) {
    player.dx = 0;
  }
}

// --- Funciones de Dibujo ---
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

// --- Lógica del Juego ---
function movePlayer() {
  player.x += player.dx;

  // Mantener al jugador dentro de los límites del canvas
  if (player.x < 0) {
    player.x = 0;
  }
  if (player.x + player.width > canvas.width) {
    player.x = canvas.width - player.width;
  }
}

function moveObstacles() {
  obstacles.forEach(obstacle => {
    obstacle.y += obstacleSpeed;
  });

  // Eliminar obstáculos que salen de la pantalla
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
    // Lógica de colisión simple
    if (
      player.x < obstacle.x + obstacle.width &&
      player.x + player.width > obstacle.x &&
      player.y < obstacle.y + obstacle.height &&
      player.y + player.height > obstacle.y
    ) {
      // Si hay colisión, el juego termina
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

// --- Bucle Principal del Juego ---
function update() {
  clearCanvas();

  spawnObstacle();
  drawObstacles();
  moveObstacles();

  drawPlayer();
  movePlayer();

  checkCollisions();

  // Llama a la siguiente animación
  requestAnimationFrame(update);
}

// Iniciar el juego
update();