import random
import webbrowser
# from speech.text_to_speech import speak

def play_random_song():
    song = random.choice(list(music_library.keys()))
    
    # speak(f"Playing {song}")
    webbrowser.open(music_library[song])
    
    return f"Playing {song}"   # 👈 UI ke liye useful


music_library = {

# 🎧 HINDI (BOLLYWOOD)
"kesariya": "https://www.youtube.com/watch?v=BddP6PYo2gs",
"tum hi ho": "https://www.youtube.com/watch?v=Umqb9KENgmk",
"raataan lambiyan": "https://www.youtube.com/watch?v=gvyUuxdRdR4",
"apna bana le": "https://www.youtube.com/watch?v=ElZfdU54Cp8",
"chaleya": "https://www.youtube.com/watch?v=VAdGW7QDJiU",
"shayad": "https://www.youtube.com/watch?v=MJyKN-8UncM",
"agar tum saath ho": "https://www.youtube.com/watch?v=sK7riqg2mr4",
"tum se hi": "https://www.youtube.com/watch?v=mt9xg0mmt28",
"phir le aya dil": "https://www.youtube.com/watch?v=3Hn9hLOljJI",
"kabira": "https://www.youtube.com/watch?v=jHNNMj5bNQw",
"channa mereya": "https://www.youtube.com/watch?v=284Ov7ysmfA",
"raabta": "https://www.youtube.com/watch?v=zlt38OOqwDc",
"tera ban jaunga": "https://www.youtube.com/watch?v=Qdz5n1Xe5Qo",
"pal": "https://www.youtube.com/watch?v=1cDoRqPnCXU",
"dil diyan gallan": "https://www.youtube.com/watch?v=SAcpESN_Fk4",
"kaise hua": "https://www.youtube.com/watch?v=WWXm39leYew",
"bekhayali": "https://www.youtube.com/watch?v=VOLSb3c6lXY",
"sun raha hai": "https://www.youtube.com/watch?v=hoNb6HuNmU0",
"lo safar": "https://www.youtube.com/watch?v=b1Jt9Fv3aH8",
"ae dil hai mushkil": "https://www.youtube.com/watch?v=6FURuLYrR_Q",

# 🔥 TRENDING / REELS
"heeriye": "https://www.youtube.com/watch?v=RLzC55ai0eo",
"obsessed": "https://www.youtube.com/watch?v=QJ7u7Z6v6lQ",
"hukum": "https://www.youtube.com/watch?v=3R7h6c9Xf4A",
"what jhumka": "https://www.youtube.com/watch?v=Zr2F1Tz1K7E",
"jhoome jo pathaan": "https://www.youtube.com/watch?v=YxWlaYCA8MU",
"besharam rang": "https://www.youtube.com/watch?v=II2EO3Nw4m0",
"oo antava": "https://www.youtube.com/watch?v=7Z0WJtZC6A8",
"srivalli": "https://www.youtube.com/watch?v=3cZ9gRfsd4Y",
"arabic kuthu": "https://www.youtube.com/watch?v=KUN5Uf9mObQ",
"butta bomma": "https://www.youtube.com/watch?v=2mDCVzruYzQ",

# 🎤 ENGLISH POP
"shape of you": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
"perfect": "https://www.youtube.com/watch?v=2Vv-BfVoq4g",
"blinding lights": "https://www.youtube.com/watch?v=4NRXx6U8ABQ",
"stay": "https://www.youtube.com/watch?v=kTJczUoc26U",
"senorita": "https://www.youtube.com/watch?v=Pkh8UtuejGw",
"bad guy": "https://www.youtube.com/watch?v=DyDfgMOUjCI",
"levitating": "https://www.youtube.com/watch?v=TUVcZfQe-Kw",
"watermelon sugar": "https://www.youtube.com/watch?v=E07s5ZYygMg",
"as it was": "https://www.youtube.com/watch?v=H5v3kku4y6Q",
"someone you loved": "https://www.youtube.com/watch?v=zABLecsR5UE",

# 💪 MOTIVATION / WORKOUT
"believer": "https://www.youtube.com/watch?v=7wtfhZwyrcc",
"unstoppable": "https://www.youtube.com/watch?v=YaEG2aWJnZ8",
"legends never die": "https://www.youtube.com/watch?v=r6zIGXun57U",
"enemy": "https://www.youtube.com/watch?v=F5tSoaJ93ac",
"remember the name": "https://www.youtube.com/watch?v=VDvr08sCPOc",
"power": "https://www.youtube.com/watch?v=nmnjL26OBcY",

# 😌 LOFI / CHILL
"lofi hip hop": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
"chill beats": "https://www.youtube.com/watch?v=5qap5aO4i9A",
"relax music": "https://www.youtube.com/watch?v=DWcJFNfaw9c",

# 🎮 GAMING / EDM
"faded": "https://www.youtube.com/watch?v=60ItHLz5WEA",
"alone": "https://www.youtube.com/watch?v=1-xGerv5FOk",
"spectre": "https://www.youtube.com/watch?v=AOeY-nDp7hI",
"on my way": "https://www.youtube.com/watch?v=dhYOPzcsbGM",
}

# play_random_song()