(function(){
  // A small collection of theme palettes. Add or tweak palettes as you like.
  const themes = [
    {
      name: 'violet-dream',
      bg: 'linear-gradient(135deg,#667eea,#764ba2)',
      primary: '#667eea',
      secondary: '#764ba2',
      accent: '#9be7ff',
      text: '#0f172a',
      cardBg: 'rgba(255,255,255,0.9)'
    },
    {
      name: 'sunset',
      bg: 'linear-gradient(135deg,#f6d365,#fda085)',
      primary: '#f6d365',
      secondary: '#fda085',
      accent: '#ffd18c',
      text: '#1b1b1b',
      cardBg: 'rgba(255,255,255,0.92)'
    },
    {
      name: 'oceanic',
      bg: 'linear-gradient(135deg,#89f7fe,#66a6ff)',
      primary: '#89f7fe',
      secondary: '#66a6ff',
      accent: '#e0f7ff',
      text: '#021427',
      cardBg: 'rgba(255,255,255,0.95)'
    },
    {
      name: 'terracotta',
      bg: 'linear-gradient(135deg,#c79081,#dfa579)',
      primary: '#c79081',
      secondary: '#dfa579',
      accent: '#ffd6b6',
      text: '#2c1f18',
      cardBg: 'rgba(255,255,255,0.93)'
    },
    {
      name: 'rose-glow',
      bg: 'linear-gradient(135deg,#fbd3e9,#bb377d)',
      primary: '#fbd3e9',
      secondary: '#bb377d',
      accent: '#ffd1e6',
      text: '#2a1220',
      cardBg: 'rgba(255,255,255,0.94)'
    },
    {
      name: 'lavender',
      bg: 'linear-gradient(135deg,#a18cd1,#fbc2eb)',
      primary: '#a18cd1',
      secondary: '#fbc2eb',
      accent: '#f7e6ff',
      text: '#1b0d25',
      cardBg: 'rgba(255,255,255,0.95)'
    }
  ];

  function pickRandomTheme(){
    return themes[Math.floor(Math.random()*themes.length)];
  }

  function applyTheme(theme){
    const root = document.documentElement;
    root.style.setProperty('--bg', theme.bg);
    root.style.setProperty('--primary', theme.primary);
    root.style.setProperty('--secondary', theme.secondary);
    root.style.setProperty('--accent', theme.accent);
    root.style.setProperty('--text', theme.text);
    root.style.setProperty('--card-bg', theme.cardBg);

    // Add a data attribute for optional CSS targeting
    root.setAttribute('data-theme', theme.name);
  }

  // Optionally allow manual change via button with id `change-vibe`
  function setupChangeButton(){
    const btn = document.getElementById('change-vibe');
    if(!btn) return;
    btn.addEventListener('click', function(e){
      e.preventDefault();
      const t = pickRandomTheme();
      applyTheme(t);
    });
  }

  // On DOM ready, apply a random theme
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){
      applyTheme(pickRandomTheme());
      setupChangeButton();
    });
  } else {
    applyTheme(pickRandomTheme());
    setupChangeButton();
  }
})();
