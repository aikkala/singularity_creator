import sys
import os
import subprocess
import argparse


# Define parts of the definition file
def_header = \
"""BootStrap: docker
From: continuumio/miniconda3

"""

def_files_hdr = \
"""%files

    # In general this isn't a good idea. We'll remove these ssh-keys later on in
    # this definition file, but I'm not sure if they are still somehow recoverable. THUS
    # YOU SHOULD NOT SHARE THE PRODUCED CONTAINER WITH ANYONE
"""

def_files_ssh_key = \
"""    {SSH_KEY_FILE} /root/.ssh/
"""

def_files_known_hosts = \
"""    {KNOWN_HOSTS_FILE} /root/.ssh/
"""

def_post = \
"""%post

    # Create a new directory for project
    mkdir Workspace && cd Workspace

    # Install git
    apt update -y && apt install -y git

    # Git clone the project
    GIT_PROJECT_NAME=`echo {GIT_PROJECT} | cut -d "/" -f 2 | cut -d "." -f 1`
    echo "Cloning project {GIT_PROJECT} into folder /Workspace/${{GIT_PROJECT_NAME}}"
    git clone {GIT_PROJECT} && cd ${{GIT_PROJECT_NAME}}

    # Update base Anaconda environment with the yaml file
    /opt/conda/bin/conda env update --name base --file {ANACONDA_ENV_FILE}

    echo ". /opt/conda/etc/profile.d/conda.sh" >> $SINGULARITY_ENVIRONMENT
    echo "conda activate" >> $SINGULARITY_ENVIRONMENT
    echo "export PYTHONPATH=/Workspace/${{GIT_PROJECT_NAME}}:${{PYTHONPATH}}" >> $SINGULARITY_ENVIRONMENT
    echo "export PROJECT_DIR=/Workspace/${{GIT_PROJECT_NAME}}" >> $SINGULARITY_ENVIRONMENT

"""

def_remove_ssh = \
"""    # Remove the ssh keys
    rm -rf /root/.ssh

"""

def_runscript = \
"""%runscript

    cd ${{PROJECT_DIR}}
    exec "$@"

"""

def_environment = \
"""%environment
    export LD_PRELOAD=\"\""""


def main(output_dir, git_project, anaconda_env_file, ssh_key_file, known_hosts_file):

    # Build the definition file
    definition = def_header

    if ssh_key_file is not None or known_hosts_file is not None:
        definition += def_files_hdr
        if ssh_key_file is not None:
            definition += def_files_ssh_key
        if known_hosts_file is not None:
            definition += def_files_known_hosts
        definition += "\n"

        definition += def_post
        definition += def_remove_ssh

    else:
        definition += def_post

    definition += def_runscript
    definition += def_environment

    # If an ssh key wasn't given, we could check here whether the repo is private or not; if it's private
    # ask the user for a ssh key file
    # TODO

    # Create the definition file and save it into output_dir
    # Use "Singularity" as the definition filename in case we want to use this for singularity-hub
    definition_file = os.path.join(output_dir, "Singularity")
    os.makedirs(output_dir, exist_ok=True)
    with open(definition_file, 'w') as file:
        file.write(definition.format(GIT_PROJECT=git_project, ANACONDA_ENV_FILE=anaconda_env_file,
                                     SSH_KEY_FILE=ssh_key_file, KNOWN_HOSTS_FILE=known_hosts_file))

    # Build the singularity container
    container_file = os.path.join(output_dir, "container.sif")
    subprocess.run(["singularity", "build", "--fakeroot", container_file, definition_file])


if __name__ == "__main__":

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Download a Git project and make it into a Singularity container with an Anaconda environment.")
    parser.add_argument('--output-dir', type=str, help='Location where the Singularity container will be created', default=".")
    parser.add_argument('--git-url', type=str, help='Git project''s url as SSH or HTML', required=True)
    parser.add_argument('--env-file', type=str, help='Anaconda environment yaml file location in the project (as a relative path)', required=True)
    parser.add_argument('--ssh-key-file', type=str, help='Location of SSH key file if downloading a private Git repository', default=None)
    parser.add_argument('--known-hosts-file', type=str, help='Location of known hosts file for non-interactive build', default=None)
    args = parser.parse_args(sys.argv[1:])

    # Run the script
    main(args.output_dir, args.git_url, args.env_file, args.ssh_key_file, args.known_hosts_file)

