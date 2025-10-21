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
const narrator = document.getElementById('narrator-callout');

let currentGameId = null;

const ABILITY_LABELS = {
  strength: 'STR',
  dexterity: 'DEX',
  constitution: 'CON',
  intelligence: 'INT',
  wisdom: 'WIS',
  charisma: 'CHA',
};

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
    setStatus('The Weave falters—unable to load heroes or monsters. Try refreshing.', true);
    if (narrator) {
      narrator.classList.remove('hidden');
      narrator.textContent = 'The Dungeon Master cannot find the minis—refresh to search again.';
    }
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
  const statsField = card.querySelector('[data-field="stats"]');
  if (statsField) {
    renderAbilityScores(statsField, data.stats);
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
    button.title = buildActionTooltip(action);
    button.addEventListener('click', () => executeAction(action.name));
    playerActions.appendChild(button);
  });
}

function abilityModifier(score) {
  if (typeof score !== 'number') {
    return 0;
  }
  return Math.floor((score - 10) / 2);
}

function renderAbilityScores(container, stats = {}) {
  container.innerHTML = '';
  const rows = Object.entries(ABILITY_LABELS).map(([key, label]) => {
    const score = stats[key];
    if (score == null) {
      return null;
    }
    const mod = abilityModifier(score);
    const row = document.createElement('div');
    row.className = 'ability-score';
    row.innerHTML = `
      <span class="ability-label">${label}</span>
      <span class="ability-value">${score}</span>
      <span class="ability-mod">${mod >= 0 ? `+${mod}` : mod}</span>
    `;
    return row;
  }).filter(Boolean);

  if (!rows.length) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');
  rows.forEach((row) => container.appendChild(row));
}

function buildActionTooltip(action) {
  const parts = [
    `${action.damage_dice}${action.damage_bonus ? `+${action.damage_bonus}` : ''} ${action.damage_type || 'damage'}`.trim(),
    action.description,
  ].filter(Boolean);
  return parts.join('\n');
}

function renderGame(game) {
  if (!game) {
    return;
  }

  battlefield.classList.remove('hidden');
  if (narrator) {
    narrator.classList.remove('hidden');
  }
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
      ? 'Victory! The adventuring party has triumphed.'
      : 'Defeat... the dungeon grows ever darker.';
    setStatus(victoryMessage, game.winner !== 'players');
    if (narrator) {
      narrator.textContent = game.winner === 'players'
        ? 'The Dungeon Master records a glorious tale of heroism.'
        : 'The Dungeon Master mourns the fallen and closes the tome.';
    }
  } else if (game.turn) {
    const isPlayer = game.turn.type === 'player';
    const turnMessage = isPlayer
      ? 'Your initiative is called! Choose your maneuver.'
      : `${game.turn.name} seizes the initiative...`;
    setStatus(turnMessage);
    if (narrator) {
      narrator.textContent = isPlayer
        ? 'Select a tactic befitting a hero of the realms.'
        : 'Hold fast—steel yourself for the coming blow.';
    }
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
    if (narrator) {
      narrator.classList.remove('hidden');
      narrator.textContent = 'The Dungeon Master pauses, sensing that fate resists that move.';
    }
  }
}

startButton.addEventListener('click', async () => {
  const playerId = playerSelect.value;
  const monsterId = monsterSelect.value;
  if (!playerId || !monsterId) {
    setStatus('Select both a hero and a foe to tempt fate.', true);
    return;
  }

  startButton.disabled = true;
  setStatus('The Dungeon Master arranges the battle map...');
  if (narrator) {
    narrator.classList.remove('hidden');
    narrator.textContent = 'Miniatures are placed upon the battle map as the Dungeon Master intones the scene.';
  }

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
    setStatus('Initiative rolled! The encounter begins.');
    renderGame(data.game);
  } catch (error) {
    console.error('Start game error', error);
    setStatus(error.message, true);
    if (narrator) {
      narrator.classList.remove('hidden');
      narrator.textContent = 'The Dungeon Master slams the rulebook shut—try once more.';
    }
  } finally {
    startButton.disabled = false;
  }
});

loadOptions();
