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
const creatorForm = document.getElementById('character-form');
const creatorClassSelect = document.getElementById('creator-class');
const creatorNameInput = document.getElementById('creator-name');
const creatorDescription = document.getElementById('creator-description');
const abilityMethodSelect = document.getElementById('ability-method');
const rollAbilitiesButton = document.getElementById('roll-abilities');
const abilityInputsContainer = document.getElementById('ability-inputs');
const skillOptionsContainer = document.getElementById('skill-options');
const skillHint = document.getElementById('skill-hint');
const weaponSelect = document.getElementById('weapon-select');
const armorSelect = document.getElementById('armor-select');
const packSelect = document.getElementById('pack-select');
const spellFieldset = document.getElementById('spell-fieldset');
const cantripOptionsContainer = document.getElementById('cantrip-options');
const spellOptionsContainer = document.getElementById('spell-options');
const cantripHint = document.getElementById('cantrip-hint');
const spellHint = document.getElementById('spell-hint');
const creationStatus = document.getElementById('creation-status');
const heroDiceForm = document.getElementById('hero-dice-form');
const heroDiceAbility = document.getElementById('hero-dice-ability');
const heroDiceAdvantage = document.getElementById('hero-dice-advantage');
const heroDiceDc = document.getElementById('hero-dice-dc');
const heroDiceProficiency = document.getElementById('hero-dice-proficiency');
const heroDiceResult = document.getElementById('hero-dice-result');
const monsterDiceForm = document.getElementById('monster-dice-form');
const monsterDiceAbility = document.getElementById('monster-dice-ability');
const monsterDiceAdvantage = document.getElementById('monster-dice-advantage');
const monsterDiceDc = document.getElementById('monster-dice-dc');
const monsterDiceProficiency = document.getElementById('monster-dice-proficiency');
const monsterDiceResult = document.getElementById('monster-dice-result');

let currentGameId = null;
let characterOptionsData = null;
let skillLimit = 0;
let cantripLimit = 0;
let spellLimit = 0;

const ABILITY_LABELS = {
  strength: 'STR',
  dexterity: 'DEX',
  constitution: 'CON',
  intelligence: 'INT',
  wisdom: 'WIS',
  charisma: 'CHA',
};

const abilityInputs = {};
const classOptionMap = new Map();

async function loadPlayers() {
  try {
    const response = await fetch('/api/players');
    const data = await response.json();
    populateSelect(playerSelect, data.players, 'Select a hero');
  } catch (error) {
    console.error('Failed to load players', error);
    setStatus('Unable to load heroes from the roster.', true);
  }
}

async function loadMonsters() {
  try {
    const response = await fetch('/api/monsters');
    const data = await response.json();
    populateSelect(monsterSelect, data.monsters, 'Select a monster');
  } catch (error) {
    console.error('Failed to load monsters', error);
    setStatus('The bestiary is missing—refresh to try again.', true);
  }
}

async function loadCharacterOptions() {
  try {
    const response = await fetch('/api/character-options');
    characterOptionsData = await response.json();
    renderCharacterCreator();
  } catch (error) {
       console.error('Failed to load character creation options', error);
    if (creationStatus) {
      creationStatus.textContent = 'Unable to load character creation data.';
      creationStatus.classList.add('error');
    }
  }
}

function renderCharacterCreator() {
  if (!characterOptionsData || !creatorForm) {
    return;
  }

  populateAbilityMethods(characterOptionsData.ability_methods || []);
  populateClassOptions(characterOptionsData.classes || []);
  renderAbilityInputs();
  updateClassOptions();

  if (!creatorForm.dataset.initialised) {
    creatorForm.addEventListener('submit', submitCharacterForm);
    creatorClassSelect.addEventListener('change', updateClassOptions);
    if (rollAbilitiesButton) {
      rollAbilitiesButton.addEventListener('click', handleRollAbilities);
    }
    creatorForm.dataset.initialised = 'true';
  }
}

function populateAbilityMethods(methods) {
  if (!abilityMethodSelect) {
    return;
  }
  abilityMethodSelect.innerHTML = '';
  methods.forEach((method) => {
    const option = document.createElement('option');
    option.value = method.id;
    option.textContent = method.label;
    abilityMethodSelect.appendChild(option);
  });
}

function populateClassOptions(classes) {
  if (!creatorClassSelect) {
    return;
  }
  creatorClassSelect.innerHTML = '';
  classOptionMap.clear();
  classes.forEach((cls) => {
    classOptionMap.set(cls.class, cls);
    const option = document.createElement('option');
    option.value = cls.class;
    option.textContent = `${cls.class} (${cls.hit_die})`;
    creatorClassSelect.appendChild(option);
  });
  if (classes.length && !creatorClassSelect.value) {
    creatorClassSelect.value = classes[0].class;
  }
}

function renderAbilityInputs() {
  if (!abilityInputsContainer) {
    return;
  }
  abilityInputsContainer.innerHTML = '';
  Object.entries(ABILITY_LABELS).forEach(([ability, label]) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'ability-input';

    const inputLabel = document.createElement('label');
    inputLabel.innerHTML = `
      <span>${label}</span>
      <span class="ability-mod" data-modifier-for="${ability}">+0</span>
    `;

    const input = document.createElement('input');
    input.type = 'number';
    input.name = ability;
    input.min = '1';
    input.max = '30';
    input.value = '10';
    input.addEventListener('input', () => updateAbilityModifier(ability));

    abilityInputs[ability] = input;
    wrapper.appendChild(inputLabel);
    wrapper.appendChild(input);
    abilityInputsContainer.appendChild(wrapper);
  });
  updateAllAbilityModifiers();
}

function updateAbilityModifier(ability) {
  const input = abilityInputs[ability];
  if (!input) {
    return;
  }
  const value = Number.parseInt(input.value, 10);
  const mod = abilityModifier(Number.isNaN(value) ? 10 : value);
  const display = abilityInputsContainer.querySelector(`[data-modifier-for="${ability}"]`);
  if (display) {
    display.textContent = mod >= 0 ? `+${mod}` : `${mod}`;
  }
}

function updateAllAbilityModifiers() {
  Object.keys(ABILITY_LABELS).forEach(updateAbilityModifier);
}

function updateClassOptions() {
  const className = creatorClassSelect ? creatorClassSelect.value : null;
  if (!className || !classOptionMap.has(className)) {
    return;
  }
  const classData = classOptionMap.get(className);
  skillLimit = classData.skill_choices || 0;
  renderSkillOptions(classData.skill_options || []);
  populateEquipmentSelect(weaponSelect, classData.weapon_options || [], 'Choose a weapon');
  populateEquipmentSelect(armorSelect, classData.armor_options || [], 'Choose armour or shield', true);
  populateEquipmentSelect(packSelect, classData.pack_options || [], 'Choose a pack', true);
  renderSpellOptions(classData.spell_options || {});
}

function renderSkillOptions(skills) {
  if (!skillOptionsContainer) {
    return;
  }
  skillOptionsContainer.innerHTML = '';
  if (!skills.length || !skillLimit) {
    skillHint.textContent = 'No skill selection required.';
    return;
  }
  skillHint.textContent = `Choose ${skillLimit} skill${skillLimit === 1 ? '' : 's'}.`;
  skills.forEach((skill, index) => {
    const id = `skill-${index}`;
    const label = document.createElement('label');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = skill;
    checkbox.id = id;
    const span = document.createElement('span');
    span.textContent = skill;
    label.appendChild(checkbox);
    label.appendChild(span);
    skillOptionsContainer.appendChild(label);
  });
  enforceLimit(skillOptionsContainer, skillLimit);
}

function populateEquipmentSelect(select, items, placeholder, allowEmpty = false) {
  if (!select) {
    return;
  }
  select.innerHTML = '';
  const placeholderOption = document.createElement('option');
  placeholderOption.value = '';
  placeholderOption.textContent = placeholder;
  placeholderOption.disabled = items.length > 0 && !allowEmpty;
  placeholderOption.selected = true;
  select.appendChild(placeholderOption);
  if (allowEmpty) {
    const noneOption = document.createElement('option');
    noneOption.value = '';
    noneOption.textContent = 'None';
    select.appendChild(noneOption);
  }
  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.name;
    let detail = '';
    if (item.damage) {
      detail = `${item.damage} ${item.damage_type || ''}`.trim();
    } else if (item.ac != null) {
      detail = `AC ${item.ac}${item.type ? `, ${item.type}` : ''}`;
    } else if (item.type) {
      detail = item.type;
    }
    option.textContent = detail ? `${item.name} (${detail})` : item.name;
    select.appendChild(option);
  });
}

function renderSpellOptions(options) {
  if (!spellFieldset) {
    return;
  }
  const limits = options.limits || {};
  cantripLimit = limits.cantrips_known || 0;
  spellLimit = limits.spell_slots || 0;
  const hasSpells = (options.cantrips && options.cantrips.length) || (options.level_1 && options.level_1.length);
  if (!hasSpells) {
    spellFieldset.classList.add('hidden');
    return;
  }
  spellFieldset.classList.remove('hidden');

  cantripOptionsContainer.innerHTML = '';
  spellOptionsContainer.innerHTML = '';

  cantripHint.textContent = cantripLimit
    ? `Choose up to ${cantripLimit} cantrip${cantripLimit === 1 ? '' : 's'}.`
    : 'No cantrips available at this level.';
  renderSpellGroup(cantripOptionsContainer, options.cantrips || [], 'cantrip');
  enforceLimit(cantripOptionsContainer, cantripLimit);

  spellHint.textContent = spellLimit
    ? `Prepare up to ${spellLimit} level 1 spell${spellLimit === 1 ? '' : 's'}.`
    : 'No 1st-level spells available to prepare.';
  renderSpellGroup(spellOptionsContainer, options.level_1 || [], 'spell');
  enforceLimit(spellOptionsContainer, spellLimit);
}

function renderSpellGroup(container, spells, prefix) {
  container.innerHTML = '';
  spells.forEach((spell, index) => {
    const id = `${prefix}-${index}`;
    const label = document.createElement('label');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = spell.name;
    checkbox.id = id;
    const span = document.createElement('span');
    span.textContent = spell.name;
    label.title = spell.description || '';
    label.appendChild(checkbox);
    label.appendChild(span);
    container.appendChild(label);
  });
}

function enforceLimit(container, limit) {
  const checkboxes = container ? Array.from(container.querySelectorAll('input[type="checkbox"]')) : [];
  if (!checkboxes.length || !limit) {
    checkboxes.forEach((cb) => {
      cb.checked = false;
      cb.disabled = limit === 0;
    });
    return;
  }
  const update = () => {
    const checkedCount = checkboxes.filter((cb) => cb.checked).length;
    checkboxes.forEach((cb) => {
      if (!cb.checked) {
        cb.disabled = checkedCount >= limit;
      }
    });
  };
  checkboxes.forEach((cb) => {
    cb.disabled = false;
    cb.addEventListener('change', update);
  });
  update();
}

function getCheckedValues(container) {
  if (!container) {
    return [];
  }
  return Array.from(container.querySelectorAll('input[type="checkbox"]:checked')).map((input) => input.value);
}

function setCreationStatus(message, isError = false) {
  if (!creationStatus) {
    return;
  }
  creationStatus.textContent = message;
  creationStatus.classList.toggle('error', isError);
}

function applyAbilityScores(scores = []) {
  if (!Array.isArray(scores) || !scores.length) {
    return;
  }
  const ordered = [...scores].sort((a, b) => b - a);
  const abilities = Object.keys(ABILITY_LABELS);
  abilities.forEach((ability, index) => {
    const value = ordered[index] != null ? ordered[index] : ordered[ordered.length - 1] || 10;
    if (abilityInputs[ability]) {
      abilityInputs[ability].value = value;
      updateAbilityModifier(ability);
    }
  });
  setCreationStatus('Ability scores rolled and assigned.');
}

async function handleRollAbilities(event) {
  event.preventDefault();
  if (!abilityMethodSelect) {
    return;
  }
  const method = abilityMethodSelect.value || '4d6-drop-lowest';
  try {
    if (rollAbilitiesButton) {
      rollAbilitiesButton.disabled = true;
    }
    setCreationStatus('Rolling ability scores...');
    const response = await fetch('/api/character-abilities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Failed to roll ability scores');
    }
    applyAbilityScores(data.scores);
  } catch (error) {
    console.error('Ability roll error', error);
    setCreationStatus(error.message, true);
  } finally {
    if (rollAbilitiesButton) {
      rollAbilitiesButton.disabled = false;
    }
  }
}

function buildAbilityScores() {
  const result = {};
  Object.keys(ABILITY_LABELS).forEach((ability) => {
    const input = abilityInputs[ability];
    const value = Number.parseInt(input?.value, 10);
    result[ability] = Number.isNaN(value) ? 10 : value;
  });
  return result;
}

async function submitCharacterForm(event) {
  event.preventDefault();
  if (!creatorClassSelect || !creatorClassSelect.value) {
    setCreationStatus('Select a class for your hero.', true);
    return;
  }
  const selectedSkills = getCheckedValues(skillOptionsContainer);
  if (skillLimit && selectedSkills.length !== skillLimit) {
    setCreationStatus(`Please choose exactly ${skillLimit} skill${skillLimit === 1 ? '' : 's'}.`, true);
    return;
  }
  const selectedCantrips = getCheckedValues(cantripOptionsContainer);
  if (cantripLimit && selectedCantrips.length > cantripLimit) {
    setCreationStatus(`Choose up to ${cantripLimit} cantrip${cantripLimit === 1 ? '' : 's'}.`, true);
    return;
  }
  const selectedSpells = getCheckedValues(spellOptionsContainer);
  if (spellLimit && selectedSpells.length > spellLimit) {
    setCreationStatus(`Choose up to ${spellLimit} prepared spell${spellLimit === 1 ? '' : 's'}.`, true);
    return;
  }

  const name = creatorNameInput ? creatorNameInput.value.trim() : '';
  if (!name) {
    setCreationStatus('Name your hero before saving.', true);
    return;
  }

  const payload = {
    name,
    class: creatorClassSelect.value,
    ability_method: abilityMethodSelect ? abilityMethodSelect.value : null,
    ability_scores: buildAbilityScores(),
    skills: selectedSkills,
    equipment: {
      weapon: weaponSelect && weaponSelect.value ? weaponSelect.value : null,
      armor: armorSelect && armorSelect.value ? armorSelect.value : null,
      pack: packSelect && packSelect.value ? packSelect.value : null,
    },
    spells: [...selectedCantrips, ...selectedSpells],
  };
  if (creatorDescription && creatorDescription.value.trim()) {
    payload.description = creatorDescription.value.trim();
  }
  try {
    setCreationStatus('Saving hero...');
    const response = await fetch('/api/characters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Failed to save character');
    }
    const character = data.character;
    setCreationStatus(`Saved ${character.name}. They are ready for battle!`);
    await loadPlayers();
    if (playerSelect && character.id) {
      playerSelect.value = character.id;
    }
    creatorForm.reset();
    renderCharacterCreator();
  } catch (error) {
    console.error('Character creation error', error);
    setCreationStatus(error.message, true);
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

function clearDiceResults() {
  if (heroDiceResult) {
    heroDiceResult.textContent = '';
    heroDiceResult.removeAttribute('title');
    heroDiceResult.dataset.hasResult = 'false';
  }
  if (monsterDiceResult) {
    monsterDiceResult.textContent = '';
    monsterDiceResult.removeAttribute('title');
    monsterDiceResult.dataset.hasResult = 'false';
  }
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

  const isPlayersTurn = Boolean(turn) && (turn.type === 'player' || turn.name === player.name);
  const currentTurnActions = new Map((turn?.actions || []).map((action) => [action.name, action]));
  (player.actions || []).forEach((action) => {
    const button = document.createElement('button');
    button.textContent = `${action.name} (+${action.attack_bonus} | ${action.damage_dice}${action.damage_bonus ? `+${action.damage_bonus}` : ''})`;
    const isActionAvailable = currentTurnActions.size === 0 || currentTurnActions.has(action.name);
    button.disabled = !isPlayersTurn || Boolean(winner) || !isActionAvailable;
    const tooltipSource = currentTurnActions.get(action.name) || action;
    button.title = buildActionTooltip(tooltipSource);
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

function populateDiceAbilitySelect(select, stats = {}) {
  if (!select) {
    return [];
  }

  const previous = select.value;
  select.innerHTML = '';

  const available = Object.entries(ABILITY_LABELS)
    .filter(([key]) => stats && typeof stats[key] === 'number')
    .map(([key, label]) => ({ key, label, score: stats[key] }));

  if (!available.length) {
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'No abilities available';
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);
    select.disabled = true;
    return [];
  }

  available.forEach(({ key, label, score }) => {
    const option = document.createElement('option');
    const mod = abilityModifier(score);
    option.value = key;
    option.textContent = `${label} (${score}${mod >= 0 ? `, +${mod}` : `, ${mod}`})`;
    select.appendChild(option);
  });

  select.disabled = false;
  const match = available.find(({ key }) => key === previous);
  select.value = match ? match.key : available[0].key;
  return available;
}

function updateDicePanel(form, abilitySelect, stats = {}, resultField) {
  if (!form || !abilitySelect) {
    return;
  }

  const available = populateDiceAbilitySelect(abilitySelect, stats);
  const enabled = available.length > 0;
  const controls = form.querySelectorAll('select, input, button');
  controls.forEach((control) => {
    control.disabled = !enabled;
  });

  if (!enabled && resultField) {
    resultField.textContent = 'No ability scores available for dice rolls.';
    resultField.dataset.hasResult = 'true';
    resultField.title = '';
  } else if (resultField && resultField.dataset.hasResult !== 'true') {
    resultField.textContent = '';
    resultField.title = '';
  }
}

function renderDicePanels(hero, monster) {
  if (heroDiceForm && heroDiceAbility) {
    updateDicePanel(heroDiceForm, heroDiceAbility, hero?.stats || {}, heroDiceResult);
  }
  if (monsterDiceForm && monsterDiceAbility) {
    updateDicePanel(monsterDiceForm, monsterDiceAbility, monster?.stats || {}, monsterDiceResult);
  }
}

function displayDiceResult(roller, roll) {
  const target = roller === 'player' ? heroDiceResult : monsterDiceResult;
  if (!target) {
    return;
  }

  if (!roll) {
    target.textContent = '';
    target.dataset.hasResult = 'false';
    target.removeAttribute('title');
    return;
  }

  const summaryParts = [];
  if (roll.roller) {
    summaryParts.push(roll.roller);
  }
  if (roll.ability) {
    summaryParts.push(`${roll.ability} test`);
  }
  const summary = summaryParts.length ? summaryParts.join(' — ') : 'Dice result';

  const detailParts = [];
  if (Array.isArray(roll.rolls) && roll.rolls.length > 1) {
    detailParts.push(`rolls ${roll.rolls.join(', ')} (kept ${roll.roll})`);
  } else if (typeof roll.roll === 'number') {
    detailParts.push(`roll ${roll.roll}`);
  }
  if (typeof roll.modifier === 'number') {
    detailParts.push(`modifier ${roll.modifier >= 0 ? `+${roll.modifier}` : roll.modifier}`);
  }
  if (typeof roll.proficiency === 'number' && roll.proficiency) {
    detailParts.push(`proficiency +${roll.proficiency}`);
  }
  if (typeof roll.total === 'number') {
    detailParts.push(`total ${roll.total}`);
  }
  if (typeof roll.dc === 'number') {
    detailParts.push(`DC ${roll.dc}`);
  }
  if (typeof roll.success === 'boolean') {
    detailParts.push(roll.success ? 'success' : 'failure');
  }

  target.textContent = `${summary}: ${detailParts.join(', ')}`;
  target.dataset.hasResult = 'true';

  const tooltip = [];
  if (roll.rule_context?.description) {
    tooltip.push(roll.rule_context.description);
  }
  if (Array.isArray(roll.rule_context?.steps) && roll.rule_context.steps.length) {
    tooltip.push(`Steps: ${roll.rule_context.steps.join(' › ')}`);
  }
  if (roll.rule_context?.advantage) {
    tooltip.push(roll.rule_context.advantage);
  }
  target.title = tooltip.join('\n');
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
  const parts = [];
  if (action.attack_roll_bonus_dice) {
    parts.push(`Adds ${action.attack_roll_bonus_dice} to the attack roll.`);
  }
  const damageSummary = `${action.damage_dice}${action.damage_bonus ? `+${action.damage_bonus}` : ''} ${action.damage_type || 'damage'}`.trim();
  if (damageSummary) {
    parts.push(damageSummary);
  }
  if (action.extra_damage_dice) {
    parts.push(`Bonus damage: ${action.extra_damage_dice}`);
  }
  if (action.description) {
    parts.push(action.description);
  }
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
  renderDicePanels(hero, foe);
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
async function handleDiceRoll(event, roller) {
  event.preventDefault();
  if (!currentGameId) {
    setStatus('Start an encounter before rolling dice.', true);
    return;
  }

  const abilitySelect = roller === 'player' ? heroDiceAbility : monsterDiceAbility;
  const advantageSelect = roller === 'player' ? heroDiceAdvantage : monsterDiceAdvantage;
  const dcInput = roller === 'player' ? heroDiceDc : monsterDiceDc;
  const proficiencyToggle = roller === 'player' ? heroDiceProficiency : monsterDiceProficiency;

  if (!abilitySelect || abilitySelect.disabled || !abilitySelect.value) {
    setStatus('Select an ability score to roll.', true);
    return;
  }

  const payload = {
    game_id: currentGameId,
    roller,
    ability: abilitySelect.value,
    advantage: advantageSelect ? advantageSelect.value : 'normal',
    proficiency: Boolean(proficiencyToggle && proficiencyToggle.checked),
  };

  if (dcInput && dcInput.value) {
    const parsed = Number.parseInt(dcInput.value, 10);
    if (Number.isNaN(parsed)) {
      setStatus('DC must be a number.', true);
      return;
    }
    payload.dc = parsed;
  }

  try {
    const response = await fetch('/api/dice-roll', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Dice roll failed');
    }
    if (data.game) {
      renderGame(data.game);
    }
    displayDiceResult(roller, data.roll);
  } catch (error) {
    console.error('Dice roll error', error);
    setStatus(error.message, true);
  }
}

if (heroDiceForm) {
  heroDiceForm.addEventListener('submit', (event) => handleDiceRoll(event, 'player'));
}

if (monsterDiceForm) {
  monsterDiceForm.addEventListener('submit', (event) => handleDiceRoll(event, 'monster'));
}
startButton.addEventListener('click', async () => {
  const playerId = playerSelect.value;
  const monsterId = monsterSelect.value;
  if (!playerId || !monsterId) {
    setStatus('Select both a hero and a foe to tempt fate.', true);
    return;
  }

  startButton.disabled = true;
  clearDiceResults();
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

loadPlayers();
loadMonsters();
loadCharacterOptions();
