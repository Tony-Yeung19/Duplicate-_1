const playerSelect = document.getElementById('player-select');
const monsterSelect = document.getElementById('monster-select');
const startButton = document.getElementById('start-game');
const statusMessage = document.getElementById('status-message');
const battlefield = document.getElementById('battlefield');
const playerCard = document.getElementById('player-card');
const monsterCard = document.getElementById('monster-card');
const playerActions = document.getElementById('player-actions');
const logList = document.getElementById('log-list');
const roundNumber = document.getElementById('round-number');
const activeTurn = document.getElementById('active-turn');

let currentGameId = null;

async function loadOptions() {
  try {
    const [playersRes, monstersRes] = await Promise.all([
      fetch('/api/players'),
      fetch('/api/monsters'),
    ]);

    const playersData = await playersRes.json();
    const monstersData = await monstersRes.json();

    populateSelect(playerSelect, playersData.players, 'Select a hero');
    populateSelect(monsterSelect, monstersData.monsters, 'Select a monster');
  } catch (error) {
    console.error('Failed to load options', error);
    setStatus('Unable to load heroes or monsters. Please refresh the page.', true);
  }
}

function populateSelect(select, items, placeholder) {
  select.innerHTML = '';
  const placeholderOption = document.createElement('option');
  placeholderOption.value = '';
  placeholderOption.textContent = placeholder;
  placeholderOption.disabled = true;
  placeholderOption.selected = true;
  select.appendChild(placeholderOption);

  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.id;
    option.textContent = `${item.name}`;
    option.dataset.info = JSON.stringify(item);
    select.appendChild(option);
  });
}

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle('error', isError);
}

function updateCard(card, data) {
  if (!data) {
    card.classList.add('hidden');
    return;
  }
  card.classList.remove('hidden');
  card.querySelector('[data-field="name"]').textContent = data.name;
  const classField = card.querySelector('[data-field="class"]');
  if (classField) {
    classField.textContent = data.class || '-';
  }
  card.querySelector('[data-field="hp"]').textContent = `${data.current_hit_points}/${data.max_hit_points}`;
  card.querySelector('[data-field="ac"]').textContent = data.armor_class;
  const description = card.querySelector('[data-field="description"]');
  if (description) {
    description.textContent = data.description || '';
  }
}

function renderLog(logEntries, winner) {
  logList.innerHTML = '';
  logEntries.forEach((entry) => {
    const li = document.createElement('li');
    li.textContent = entry;
    if (winner && entry.toLowerCase().includes('victorious')) {
      li.classList.add('win');
    }
    if (winner && entry.toLowerCase().includes('defeat')) {
      li.classList.add('lose');
    }
    logList.appendChild(li);
  });
}

function renderActions(player, turn, winner) {
  playerActions.innerHTML = '';
  if (!player) {
    return;
  }

  const isPlayersTurn = turn && turn.type === 'player';
  player.actions.forEach((action) => {
    const button = document.createElement('button');
    button.textContent = `${action.name} (+${action.attack_bonus} | ${action.damage_dice}${action.damage_bonus ? `+${action.damage_bonus}` : ''})`;
    button.disabled = !isPlayersTurn || Boolean(winner);
    button.addEventListener('click', () => executeAction(action.name));
    playerActions.appendChild(button);
  });
}

function renderGame(game) {
  if (!game) {
    return;
  }

  battlefield.classList.remove('hidden');
  const hero = game.players[0];
  const foe = game.monsters[0];
  updateCard(playerCard, hero);
  updateCard(monsterCard, foe);
  renderActions(hero, game.turn, game.winner);
  renderLog(game.log, game.winner);
  roundNumber.textContent = game.round;
  activeTurn.textContent = game.turn ? `${game.turn.name} (${game.turn.type})` : 'Encounter finished';

  if (game.winner) {
    const victoryMessage = game.winner === 'players'
      ? 'Victory! The heroes stand triumphant.'
      : 'Defeat... the monsters claim the day.';
    setStatus(victoryMessage, game.winner !== 'players');
  } else if (game.turn) {
    const isPlayer = game.turn.type === 'player';
    setStatus(isPlayer ? 'It\'s your turn!' : `${game.turn.name} prepares to strike...`);
  }
}

async function executeAction(actionName) {
  if (!currentGameId) {
    return;
  }
  try {
    const response = await fetch('/api/player-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: currentGameId, action_name: actionName }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Action failed');
    }
    renderGame(data.game);
  } catch (error) {
    console.error('Action error', error);
    setStatus(error.message, true);
  }
}

startButton.addEventListener('click', async () => {
  const playerId = playerSelect.value;
  const monsterId = monsterSelect.value;
  if (!playerId || !monsterId) {
    setStatus('Choose both a hero and a monster to begin.', true);
    return;
  }

  startButton.disabled = true;
  setStatus('Preparing the battlefield...');

  try {
    const response = await fetch('/api/start-game', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId, monster_id: monsterId }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Failed to start game');
    }
    currentGameId = data.game.id;
    setStatus('Encounter started!');
    renderGame(data.game);
  } catch (error) {
    console.error('Start game error', error);
    setStatus(error.message, true);
  } finally {
    startButton.disabled = false;
  }
});

loadOptions();
