# 🤖 **SUB_Mecha** 🤖
### **A telegram Utility and Group Management bot**

![Made with python](https://www.python.org/) | ![Built by caidol](https://github.com/caidol)

## **Requirements:**
***
1. Create a telegram bot using botfather
  > First run `/newbot` and provide a bot name
  
  > after that provide a bot username

![image](https://github.com/caidol/SUB_Mecha/assets/127414645/9d004d6c-1138-400a-b66b-7cdd9b8eb14d)

> You will receive a bot token which must be saved.
***
2. Create an OWM API Token

Look at the instructions to get access the API and generate a token on ![Open weather map](https://openweathermap.org/)

***
***

## **Running the bot:**

Edit all the values in config.yml to the correct values. Most important are the bot and OWM API token.

> NOTE: use the config.yml and NOT the sample_config.yml. The sample_config is only there to provide an example.

![image](https://github.com/caidol/SUB_Mecha/assets/127414645/9496b7f4-53ca-432a-a8cd-cb9e897928d0)

### **Direct run - no use of Docker**

1. Install requirements.txt

It is recommended to create a venv for this so ensure that ![venv](https://docs.python.org/3/library/venv.html) is installed

```console
ai-dan@fedora~$ cd {program_directory}
ai-dan@fedora~$ python3 -m venv {venv_name}
ai-dan@fedora~$ source venv/bin/activate
ai-dan@fedora~$ (venv) pip install -r requirements.txt
```
> If you don't wish to run a virtual environment then run the last command without running any others.

2. Create the bot as a python package

> Do this only if it hasn't already been created as a package.

```console
ai-dan@fedora~$ pip install -e .
```

3. Run the bot, ensuring that the user is in their virtual environment (venv).

```console
ai-dan@fedora~$ python3 -m src
```

### **Docker run - use of Docker**

First ensure that docker is installed. An install guide is ![here](https://docs.docker.com/get-docker/)

1. Create the docker container

```console
ai-dan@fedora~$ sudo docker build -t {container-name} .
```

2. Run the docker container

```console
aidan@fedora~$ sudo docker run {container-name}
```

***
***

## **Deploy to cloud**

This program uses ![PythonAnywhere](https://www.pythonanywhere.com/) which is simple to set up and great for running small Python programs with its free plan. 

Ensure that you have created an account on PythonAnywhere and at least used their free plan, otherwise other plans work just fine
and could provide better processing power.

First, you must zip up the whole application recursively to upload it to PythonAnywhere, and then unzip it on the platform to run it.

```console
ai-dan@fedora~$ cd {program_directory}
ai-dan@fedora~$ zip -r {zip_filename} {directory_path}
```

If you go to the `Files` section of PythonAnywhere, then you'll see the option to upload files as shown below

![image](https://github.com/caidol/SUB_Mecha/assets/127414645/64c5544b-ac75-4a27-a02d-1684da455ebd)

After uploading the files you must unzip them as shown below

```console
ai-dan@fedora~$ unzip -D {zip_filename}
ai-dan@fedora~$ cd {unzipped_file}
```

From here you can use the manual method as explained above to run the bot. When you close the web application then you notice that the bot will still be running.

***
***
***

Thanks for checking out the program. If possible a star would be appreciated.
