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
const characterForm = document.getElementById('character-form');
const characterNameInput = document.getElementById('character-name');
const characterClassSelect = document.getElementById('character-class');
const abilityMethodSelect = document.getElementById('ability-method');
const rollAbilityButton = document.getElementById('roll-ability-scores');
const abilityInputs = abilityInputMap();
const skillLimitLabel = document.getElementById('skill-limit');
const skillOptions = document.getElementById('skill-options');
const weaponChoice = document.getElementById('weapon-choice');
const armorChoice = document.getElementById('armor-choice');
const packChoice = document.getElementById('pack-choice');
const spellContainer = document.getElementById('spell-container');
const spellHelper = document.getElementById('spell-helper');
const cantripOptions = document.getElementById('cantrip-options');
const spellOptions = document.getElementById('spell-options');
const creationStatus = document.getElementById('creation-status');
const descriptionField = document.getElementById('character-description');

let currentGameId = null;
let currentClassDetail = null;
let skillLimit = 0;
let cantripLimit = 0;
let spellLimit = 0;
let pointBuyDetails = null;

const ABILITY_LABELS = {
  strength: 'STR',
  dexterity: 'DEX',
  constitution: 'CON',
  intelligence: 'INT',
  wisdom: 'WIS',
  charisma: 'CHA',
};

function abilityInputMap() {
  return {
    strength: document.getElementById('ability-strength'),
    dexterity: document.getElementById('ability-dexterity'),
    constitution: document.getElementById('ability-constitution'),
    intelligence: document.getElementById('ability-intelligence'),
    wisdom: document.getElementById('ability-wisdom'),
    charisma: document.getElementById('ability-charisma'),
  };
}

async function loadOptions() {
  try {
    const [playersRes, monstersRes, classesRes] = await Promise.all([
      fetch('/api/players'),
      fetch('/api/monsters'),
      characterClassSelect ? fetch('/api/classes') : Promise.resolve({ ok: true, json: async () => ({ classes: [] }) }),
    ]);

    const playersData = await playersRes.json();
    const monstersData = await monstersRes.json();
    const classesData = await classesRes.json();

    populateSelect(playerSelect, playersData.players, 'Select a hero');
    populateSelect(monsterSelect, monstersData.monsters, 'Select a monster');
    if (characterClassSelect) {
      populateClassSelect(characterClassSelect, classesData.classes || []);
    }
  } catch (error) {
    console.error('Failed to load options', error);
    setStatus('The Weave falters—unable to load heroes or monsters. Try refreshing.', true);
    if (narrator) {
      narrator.classList.remove('hidden');
      narrator.textContent = 'The Dungeon Master cannot find the minis—refresh to search again.';
    }
  }
}

async function refreshPlayers(selectedId = '') {
  if (!playerSelect) {
    return;
  }
  try {
    const response = await fetch('/api/players');
    const data = await response.json();
    populateSelect(playerSelect, data.players, 'Select a hero', selectedId || playerSelect.value);
  } catch (error) {
    console.error('Failed to refresh players', error);
    setCreationStatus('Unable to refresh the hero roster right now.', true);
  }
}

function populateSelect(select, items, placeholder, selectedValue = '') {
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

  if (selectedValue) {
    select.value = selectedValue;
    if (select.value) {
      placeholderOption.selected = false;
    }
  }
}

function populateClassSelect(select, classes) {
  const previousValue = select.value;
  select.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Select a class';
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  (classes || []).forEach((cls) => {
    const option = document.createElement('option');
    option.value = cls.name;
    option.textContent = cls.name;
    option.dataset.info = JSON.stringify(cls);
    select.appendChild(option);
  });

  if (previousValue) {
    select.value = previousValue;
    if (!select.value) {
      placeholder.selected = true;
    }
  }
}

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle('error', isError);
}

function setCreationStatus(message, isError = false) {
  if (!creationStatus) {
    return;
  }
  creationStatus.textContent = message;
  creationStatus.classList.toggle('error', isError);
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

function handleLimitedCheckboxChange(event) {
  if (!event.target.matches('input[type="checkbox"]')) {
    return;
  }
  const container = event.currentTarget;
  const limit = Number(container.dataset.limit || 0);
  if (!limit) {
    return;
  }
  const checked = container.querySelectorAll('input[type="checkbox"]:checked');
  if (checked.length > limit) {
    event.target.checked = false;
    const label = container.dataset.label || 'options';
    setCreationStatus(`You may choose up to ${limit} ${label}.`, true);
  } else if (!creationStatus || !creationStatus.textContent) {
    setCreationStatus('', false);
  }
}

function addOptionCheckbox(container, value, labelText, description = '') {
  const label = document.createElement('label');
  label.className = 'option-pill';
  const input = document.createElement('input');
  input.type = 'checkbox';
  input.value = value;
  label.appendChild(input);
  const text = document.createElement('span');
  text.textContent = labelText;
  label.appendChild(text);
  if (description) {
    label.title = description;
  }
  container.appendChild(label);
}

function renderSkillOptions(skills = []) {
  if (!skillOptions) {
    return;
  }
  skillOptions.innerHTML = '';
  skillOptions.dataset.limit = skillLimit || 0;
  skillOptions.dataset.label = 'skills';
  if (!skills.length) {
    const note = document.createElement('p');
    note.className = 'muted-note';
    note.textContent = 'This class grants its skills automatically.';
    skillOptions.appendChild(note);
    return;
  }
  skills.forEach((skill) => {
    addOptionCheckbox(skillOptions, skill, skill);
  });
}

function populateEquipmentSelect(select, items, placeholder, formatter) {
  if (!select) {
    return;
  }
  select.innerHTML = '';
  const option = document.createElement('option');
  option.value = '';
  option.textContent = placeholder;
  option.disabled = false;
  option.selected = true;
  select.appendChild(option);

  (items || []).forEach((item) => {
    const choice = document.createElement('option');
    choice.value = item.name;
    choice.textContent = formatter(item);
    select.appendChild(choice);
  });
}

function renderEquipmentOptions(detail) {
  populateEquipmentSelect(
    weaponChoice,
    detail.weapon_options,
    'Choose a weapon',
    (weapon) => `${weapon.name} (${weapon.damage} ${weapon.damage_type || ''})`.trim()
  );
  populateEquipmentSelect(
    armorChoice,
    detail.armor_options,
    'Choose armor',
    (armor) => `${armor.name} (AC ${armor.ac}${armor.type ? `, ${armor.type}` : ''})`
  );
  populateEquipmentSelect(
    packChoice,
    detail.pack_options,
    'Choose a pack',
    (pack) => pack.name
  );
}

function renderSpellOptions(detail) {
  if (!spellContainer) {
    return;
  }
  cantripLimit = 0;
  spellLimit = 0;
  cantripOptions.innerHTML = '';
  spellOptions.innerHTML = '';
  cantripOptions.dataset.limit = 0;
  spellOptions.dataset.limit = 0;
  cantripOptions.dataset.label = 'cantrips';
  spellOptions.dataset.label = 'spells';

  const features = detail.spellcasting || [];
  if (!features.length) {
    spellContainer.classList.add('hidden');
    spellHelper.textContent = '';
    return;
  }

  const primary = features.find((feature) => feature.cantrips_known != null || feature.spell_slots);
  if (primary) {
    cantripLimit = Number(primary.cantrips_known || 0);
    const slots = primary.spell_slots;
    if (Array.isArray(slots) && slots.length) {
      spellLimit = Number(slots[0] || 0);
    } else if (typeof slots === 'number') {
      spellLimit = Number(slots);
    } else {
      spellLimit = 0;
    }
  }

  cantripOptions.dataset.limit = cantripLimit;
  spellOptions.dataset.limit = spellLimit;

  const messages = [];
  if (cantripLimit) {
    messages.push(`Choose ${cantripLimit} cantrip${cantripLimit > 1 ? 's' : ''}`);
  }
  if (spellLimit) {
    messages.push(`Prepare ${spellLimit} 1st-level spell${spellLimit > 1 ? 's' : ''}`);
  }
  spellHelper.textContent = messages.join(' • ');

  if (cantripLimit && detail.cantrips) {
    detail.cantrips.forEach((spell) => {
      addOptionCheckbox(cantripOptions, spell.name, spell.name, spell.description);
    });
  } else if (!cantripLimit) {
    const note = document.createElement('p');
    note.className = 'muted-note';
    note.textContent = 'No cantrips required at this level.';
    cantripOptions.appendChild(note);
  }

  if (spellLimit && detail.level_one_spells) {
    detail.level_one_spells.forEach((spell) => {
      addOptionCheckbox(spellOptions, spell.name, spell.name, spell.description);
    });
  } else if (!spellLimit) {
    const note = document.createElement('p');
    note.className = 'muted-note';
    note.textContent = 'No 1st-level spells need to be prepared.';
    spellOptions.appendChild(note);
  }

  spellContainer.classList.remove('hidden');
}

function getCheckedValues(container) {
  if (!container) {
    return [];
  }
  return Array.from(container.querySelectorAll('input[type="checkbox"]:checked')).map((input) => input.value);
}

function assignAbilityScores(scores) {
  const order = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'];
  const sorted = [...(scores || [])].sort((a, b) => b - a);
  order.forEach((ability, index) => {
    const input = abilityInputs[ability];
    if (input) {
      const value = sorted[index];
      if (value != null) {
        input.value = value;
      }
    }
  });
}

function gatherAbilityScores() {
  const abilities = {};
  Object.entries(abilityInputs).forEach(([key, input]) => {
    if (!input) {
      return;
    }
    const value = parseInt(input.value, 10);
    if (Number.isNaN(value)) {
      throw new Error(`Provide a value for ${key.toUpperCase()}.`);
    }
    abilities[key] = value;
  });
  return abilities;
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

async function loadClassDetails(className) {
  if (!className) {
    currentClassDetail = null;
    skillLimit = 0;
    cantripLimit = 0;
    spellLimit = 0;
    if (skillLimitLabel) {
      skillLimitLabel.textContent = '0';
    }
    if (skillOptions) {
      skillOptions.innerHTML = '';
      skillOptions.dataset.limit = 0;
      const prompt = document.createElement('p');
      prompt.className = 'muted-note';
      prompt.textContent = 'Select a class to view skill choices.';
      skillOptions.appendChild(prompt);
    }
    renderEquipmentOptions({ weapon_options: [], armor_options: [], pack_options: [] });
    if (spellContainer) {
      spellContainer.classList.add('hidden');
      spellHelper.textContent = '';
      cantripOptions.innerHTML = '';
      spellOptions.innerHTML = '';
    }
    return;
  }

  try {
    const response = await fetch(`/api/classes/${encodeURIComponent(className)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Unable to load class information.');
    }
    currentClassDetail = data.class || {};
    skillLimit = Number(currentClassDetail.skill_choices || 0);
    if (skillLimitLabel) {
      skillLimitLabel.textContent = String(skillLimit);
    }
    renderSkillOptions(currentClassDetail.skills || []);
    renderEquipmentOptions(currentClassDetail);
    renderSpellOptions(currentClassDetail);
    setCreationStatus('', false);
  } catch (error) {
    console.error('Class load error', error);
    setCreationStatus(error.message, true);
  }
}

if (skillOptions) {
  skillOptions.addEventListener('change', handleLimitedCheckboxChange);
}
if (cantripOptions) {
  cantripOptions.addEventListener('change', handleLimitedCheckboxChange);
}
if (spellOptions) {
  spellOptions.addEventListener('change', handleLimitedCheckboxChange);
}

if (characterClassSelect) {
  characterClassSelect.addEventListener('change', () => {
    const selectedClass = characterClassSelect.value;
    loadClassDetails(selectedClass);
  });
  loadClassDetails('');
}

if (rollAbilityButton && abilityMethodSelect) {
  rollAbilityButton.addEventListener('click', async () => {
    const method = abilityMethodSelect.value;
    if (!method) {
      setCreationStatus('Select an ability generation method first.', true);
      return;
    }
    if (method === 'point-buy') {
      try {
        if (!pointBuyDetails) {
          const response = await fetch('/api/point-buy');
          pointBuyDetails = await response.json();
        }
        Object.values(abilityInputs).forEach((input) => {
          if (input) {
            input.value = 8;
          }
        });
        const costs = pointBuyDetails && pointBuyDetails.costs
          ? Object.entries(pointBuyDetails.costs)
              .map(([score, cost]) => `${score} (${cost})`)
              .join(', ')
          : '8(0) to 15(9)';
        const budget = pointBuyDetails ? pointBuyDetails.budget : 27;
        setCreationStatus(`Point Buy: ${budget} points available. Costs: ${costs}.`);
      } catch (error) {
        console.error('Point buy info error', error);
        setCreationStatus('Unable to load point buy details.', true);
      }
      return;
    }

    rollAbilityButton.disabled = true;
    setCreationStatus('Rolling ability scores...');
    try {
      const response = await fetch('/api/ability-scores', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Unable to roll ability scores.');
      }
      assignAbilityScores(data.scores || []);
      setCreationStatus('Freshly rolled scores assigned. Adjust as desired.');
    } catch (error) {
      console.error('Ability roll error', error);
      setCreationStatus(error.message, true);
    } finally {
      rollAbilityButton.disabled = false;
    }
  });
}

if (characterForm) {
  characterForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    setCreationStatus('');

    if (!characterNameInput || !characterNameInput.value.trim()) {
      setCreationStatus('Name your hero before saving.', true);
      return;
    }
    if (!characterClassSelect || !characterClassSelect.value) {
      setCreationStatus('Choose a class to define your hero.', true);
      return;
    }

    let abilities;
    try {
      abilities = gatherAbilityScores();
    } catch (error) {
      setCreationStatus(error.message, true);
      return;
    }

    const selectedSkills = getCheckedValues(skillOptions);
    if (skillLimit && selectedSkills.length < skillLimit) {
      setCreationStatus(`Select ${skillLimit} skill${skillLimit > 1 ? 's' : ''}.`, true);
      return;
    }

    const selectedCantrips = getCheckedValues(cantripOptions);
    if (cantripLimit && selectedCantrips.length < cantripLimit) {
      setCreationStatus(`Choose ${cantripLimit} cantrip${cantripLimit > 1 ? 's' : ''}.`, true);
      return;
    }

    const selectedSpells = getCheckedValues(spellOptions);
    if (spellLimit && selectedSpells.length < spellLimit) {
      setCreationStatus(`Prepare ${spellLimit} spell${spellLimit > 1 ? 's' : ''}.`, true);
      return;
    }

    const payload = {
      name: characterNameInput.value.trim(),
      class: characterClassSelect.value,
      description: descriptionField ? descriptionField.value.trim() : '',
      abilities,
      skills: selectedSkills,
      equipment: {
        weapon: weaponChoice ? weaponChoice.value : null,
        armor: armorChoice ? armorChoice.value : null,
        pack: packChoice ? packChoice.value : null,
      },
      spells: [...selectedCantrips, ...selectedSpells],
    };

    try {
      const response = await fetch('/api/characters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to forge hero.');
      }

      setCreationStatus(`Hero ${data.character.name} has joined your roster!`);
      characterNameInput.value = '';
      if (descriptionField) {
        descriptionField.value = '';
      }
      if (skillOptions) {
        skillOptions.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
          checkbox.checked = false;
        });
      }
      if (cantripOptions) {
        cantripOptions.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
          checkbox.checked = false;
        });
      }
      if (spellOptions) {
        spellOptions.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
          checkbox.checked = false;
        });
      }
      if (weaponChoice) {
        weaponChoice.value = '';
      }
      if (armorChoice) {
        armorChoice.value = '';
      }
      if (packChoice) {
        packChoice.value = '';
      }

      await refreshPlayers(data.character.id);
      if (playerSelect) {
        playerSelect.value = data.character.id;
      }
      setStatus('Custom hero ready for battle!');
    } catch (error) {
      console.error('Create hero error', error);
      setCreationStatus(error.message, true);
    }
  });
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
