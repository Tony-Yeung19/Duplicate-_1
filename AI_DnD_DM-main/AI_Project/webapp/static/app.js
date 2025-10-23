const setupForm = document.getElementById('setup-form');
const characterOptions = document.getElementById('character-options');
const monsterOptions = document.getElementById('monster-options');
const environmentInput = document.getElementById('environment-input');
const setupStatus = document.getElementById('setup-status');

const gameArea = document.getElementById('game-area');
const heroList = document.getElementById('hero-list');
const monsterList = document.getElementById('monster-list');
const combatRound = document.getElementById('combat-round');
const currentTurn = document.getElementById('current-turn');
const victoryBanner = document.getElementById('victory-banner');
const eventLog = document.getElementById('event-log');

const actionForm = document.getElementById('action-form');
const actionInput = document.getElementById('action-input');
const actionStatus = document.getElementById('action-status');

let gameId = null;
let latestLogIndex = -1;
let currentGame = null;

const STATUS_ICON = {
  hero: {
    healthy: '🛡️',
    bloodied: '🩸',
    down: '💀',
  },
  monster: {
    threatening: '👹',
    bloodied: '🩸',
    defeated: '☠️',
  },
};

async function initialise() {
  await loadSetupData();
  attachEventListeners();
}

function attachEventListeners() {
  if (setupForm) {
    setupForm.addEventListener('submit', handleSetupSubmit);
  }
  if (actionForm) {
    actionForm.addEventListener('submit', handleActionSubmit);
  }
}

async function loadSetupData() {
  try {
    const response = await fetch('/api/setup');
    if (!response.ok) {
      throw new Error('Failed to reach the server');
    }
    const data = await response.json();
    renderCharacterOptions(data.characters || []);
    renderMonsterOptions(data.monsters || []);
    setSetupStatus('Choose your allies and adversaries.', false);
  } catch (error) {
    console.error('Failed to load setup data', error);
    setSetupStatus('Unable to load characters or monsters. Refresh to try again.', true);
  }
}

function renderCharacterOptions(characters) {
  if (!characterOptions) return;
  characterOptions.innerHTML = '';
  if (!characters.length) {
    characterOptions.textContent = 'No heroes available.';
    return;
  }
  characters.forEach((character) => {
    const label = document.createElement('label');
    label.className = 'option-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = 'characters';
    checkbox.value = character.id;

    const wrapper = document.createElement('div');
    wrapper.className = 'option-content';
    wrapper.innerHTML = `
      <span class="option-title">${character.name}</span>
      <span class="option-subtitle">${character.class || 'Adventurer'} · HP ${character.max_hit_points || '?'} · AC ${character.armor_class || '?'}</span>
    `;

    label.appendChild(checkbox);
    label.appendChild(wrapper);
    characterOptions.appendChild(label);
  });
}

function renderMonsterOptions(monsters) {
  if (!monsterOptions) return;
  monsterOptions.innerHTML = '';
  if (!monsters.length) {
    monsterOptions.textContent = 'No monsters found in the bestiary.';
    return;
  }
  monsters.forEach((monster) => {
    const label = document.createElement('label');
    label.className = 'option-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = 'monsters';
    checkbox.value = monster.id;

    const wrapper = document.createElement('div');
    wrapper.className = 'option-content';
    wrapper.innerHTML = `
      <span class="option-title">${monster.name}</span>
      <span class="option-subtitle">${monster.type || 'Creature'} · HP ${monster.hit_points || '?'} · AC ${monster.armor_class || '?'}</span>
    `;

    label.appendChild(checkbox);
    label.appendChild(wrapper);
    monsterOptions.appendChild(label);
  });
}

async function handleSetupSubmit(event) {
  event.preventDefault();
  const selectedCharacters = getCheckedValues('characters');
  const selectedMonsters = getCheckedValues('monsters');

  if (!selectedCharacters.length) {
    setSetupStatus('Select at least one hero to continue.', true);
    return;
  }
  if (!selectedMonsters.length) {
    setSetupStatus('Choose at least one monster to face the party.', true);
    return;
  }

  const payload = {
    character_ids: selectedCharacters,
    monster_ids: selectedMonsters,
    environment: environmentInput && environmentInput.value.trim() ? environmentInput.value.trim() : null,
  };

  setSetupStatus('Preparing the battlefield…', false);

  try {
    const response = await fetch('/api/start-game', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Unable to start the game.');
    }
    latestLogIndex = -1;
    gameId = data.game.id;
    renderGame(data.game);
    setSetupStatus('Encounter ready! Declare your first action.', false);
    if (gameArea) {
      gameArea.classList.remove('hidden');
    }
  } catch (error) {
    console.error('Failed to start game', error);
    setSetupStatus(error.message || 'Unable to start the encounter.', true);
  }
}

function getCheckedValues(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((input) => input.value);
}

function renderGame(game) {
  currentGame = game;
  updateStatusBar(game);
  renderCombatantList(heroList, game.characters || [], 'hero');
  renderCombatantList(monsterList, game.monsters || [], 'monster');
  renderLog(game.log || []);
  updateActionForm(game);
}

function updateStatusBar(game) {
  if (game.combat_active && game.round) {
    combatRound.textContent = `Round ${game.round}`;
    combatRound.classList.remove('hidden');
  } else {
    combatRound.textContent = '';
    combatRound.classList.add('hidden');
  }

  if (game.current_turn) {
    currentTurn.textContent = `Current turn: ${game.current_turn}`;
    currentTurn.classList.remove('hidden');
  } else {
    currentTurn.textContent = '';
    currentTurn.classList.add('hidden');
  }

  if (game.winner) {
    const message = game.winner === 'players' ? 'Heroes are victorious!' : game.winner === 'monsters' ? 'The monsters prevail!' : 'The encounter ends in a draw.';
    victoryBanner.textContent = message;
    victoryBanner.classList.remove('hidden');
  } else {
    victoryBanner.textContent = '';
    victoryBanner.classList.add('hidden');
  }
}

function renderCombatantList(container, entries, type) {
  if (!container) return;
  container.innerHTML = '';
  entries.forEach((entry) => {
    const listItem = document.createElement('li');
    listItem.className = `combatant ${entry.status || 'unknown'}`;
    const icon = STATUS_ICON[type][entry.status] || (type === 'hero' ? '🛡️' : '👹');
    const hpLabel = type === 'hero' ? `${entry.hit_points}/${entry.max_hit_points}` : `${entry.hp}/${entry.max_hp}`;
    const ac = entry.armor_class != null ? entry.armor_class : '?';

    listItem.innerHTML = `
      <div class="combatant-name">${icon} ${entry.name || 'Unknown'}</div>
      <div class="combatant-meta">HP ${hpLabel} · AC ${ac}</div>
    `;
    container.appendChild(listItem);
  });
}

function renderLog(logEntries) {
  if (!eventLog) return;
  const newEntries = logEntries.filter((entry) => typeof entry.index === 'number' && entry.index > latestLogIndex);
  if (!newEntries.length) {
    return;
  }
  newEntries.sort((a, b) => a.index - b.index);
  newEntries.forEach((entry) => {
    eventLog.appendChild(buildLogEntry(entry));
    latestLogIndex = Math.max(latestLogIndex, entry.index);
  });
  eventLog.scrollTop = eventLog.scrollHeight;
}

function buildLogEntry(entry) {
  const container = document.createElement('article');
  container.className = `log-entry ${entry.type || 'turn'}`;

  if (entry.type === 'system') {
    container.innerHTML = `<p class="system-message">${entry.message || 'A shift in the air...'}</p>`;
    return container;
  }

  const roundText = entry.round ? `Round ${entry.round}` : 'Narration';
  const header = document.createElement('header');
  header.innerHTML = `<strong>${entry.actor || 'Adventurer'}</strong><span>${roundText}</span>`;

  const action = document.createElement('p');
  action.className = 'action-text';
  action.textContent = entry.action || '';

  const narration = document.createElement('p');
  narration.className = 'narration-text';
  narration.textContent = entry.narration || '';

  container.appendChild(header);
  if (entry.action) container.appendChild(action);
  if (entry.narration) container.appendChild(narration);

  if (entry.commands && entry.commands.length) {
    const commandList = document.createElement('ul');
    commandList.className = 'command-list';
    entry.commands.forEach((command) => {
      const item = document.createElement('li');
      item.textContent = command;
      commandList.appendChild(item);
    });
    container.appendChild(commandList);
  }

  if (entry.results && entry.results.length) {
    const resultList = document.createElement('ul');
    resultList.className = 'result-list';
    entry.results.forEach((result) => {
      const item = document.createElement('li');
      item.textContent = result.message || '';
      resultList.appendChild(item);
    });
    container.appendChild(resultList);
  }

  return container;
}

async function handleActionSubmit(event) {
  event.preventDefault();
  if (!gameId) {
    setActionStatus('Start an encounter before sending actions.', true);
    return;
  }

  const actionText = actionInput ? actionInput.value.trim() : '';
  if (!actionText) {
    setActionStatus('Describe an action for the party to attempt.', true);
    return;
  }

  setActionStatus('Consulting the Dungeon Master…', false);
  actionForm.classList.add('pending');

  try {
    const response = await fetch('/api/player-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, action: actionText }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'The Dungeon Master is speechless.');
    }
    if (actionInput) {
      actionInput.value = '';
    }
    if (data.game) {
      renderGame(data.game);
    }
    setActionStatus('Action resolved.', false);
  } catch (error) {
    console.error('Failed to resolve action', error);
    setActionStatus(error.message || 'Unable to resolve that action.', true);
  } finally {
    actionForm.classList.remove('pending');
  }
}

function updateActionForm(game) {
  if (!actionInput || !actionForm) return;
  const disabled = Boolean(game.winner);
  actionInput.disabled = disabled;
  const button = actionForm.querySelector('button[type="submit"]');
  if (button) {
    button.disabled = disabled;
  }
  if (disabled) {
    setActionStatus('The encounter is complete.', false);
  } else {
    setActionStatus('Awaiting your next command.', false);
  }
}

function setSetupStatus(message, isError) {
  if (!setupStatus) return;
  setupStatus.textContent = message;
  setupStatus.classList.toggle('error', Boolean(isError));
}

function setActionStatus(message, isError) {
  if (!actionStatus) return;
  actionStatus.textContent = message;
  actionStatus.classList.toggle('error', Boolean(isError));
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialise);
} else {
  initialise();
}
