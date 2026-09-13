Just a fun lil side project I worked on when I got a new security camera with a not so good app, do plan on working on it again eventually


Features:
- Motion Detection
- Clip saving, by using a buffer and only saving on motion
- Discord integration
- Automatic camera IP detection in case of disconnects*


* The code for getting the camera's IP is AI generated

TODO:
- Use a lightweight image recognition model (have to locally train so it works on the weak hardware it would run on) to identify the gate position when it changes
- Make the code easier to edit/more modular
- Rework the function for getting the cam's IP now that I have a better grasp on networking
- Not sure if it runs on linux right now so I would need to fix that if it doesn't
