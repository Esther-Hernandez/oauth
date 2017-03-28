Item Catalog Project

Introduction

Develop an application that provides a list of items within a variety
of categories as well as provide a user registration and authentication
system. Registered users will have the ability to post, edit and delete
their own items.

What's Included

The Item Catalog Project was created for the Full Stack Developer course at Udacity. 
The project contains the following files:

database_setup.py
This file is used to set up the database schema.
The database contains three tables: User, Brand, BrandItem.
It creates the file catalog.db
project.py
This file is used to create a database session to perform CRUD operations
on a list of brands and its items.
It also manages user authorization and authentication.
templates
This folder contains html templates for the application.
static
This folder contains the styles for the application

Requirements

The project is intended to run using tools called Vagrant and Virtual Box.

Installation/Set Up

1.To fetch the source code and VM configuration, use the following from a terminal:

	git clone https://github.com/udacity/OAuth2.0 oauth

This will create a directory named oauth with necessary code and tools.

2.To launch the VM, use the following:

	vagrant up

3.When the VM is running, use the following to log into the VM:

	vagrant ssh

4.Once logged in, change to the /vagrant directory by typing the following:

	cd /vagrant

The files for the application should be under this shared folder between the VM
and the host machine.

Google+ OAuth Setup

The application uses Google+ Sign-In button for authentication.
Follow this guide to enable the Google+ API and set up the service:

	https://developers.google.com/+/web/samples/python

It is important to rename the json file downloaded from the google developers console
to the following:

	client_secrets.json

The Client ID and client_secret will be contained in this file. Replace the meta tag in main.html
with the Client ID assigned.

Running Application

For the database to be created, use the following:

	python database_setup.py

To run the the app, use the following and browse to localhost.

	python project.py


