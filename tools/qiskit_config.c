/*-------------qiskit_config.c------------------------------------------------//

 Purpose: This file will create parse keywords and output a JSON file for qiskit
          condifuration. This json file is usually placed in:
              ~/.qiskit/qiskit-ibm.json

   Notes: Compile with:
              gcc qiskit_config.c -o qiskit_config

//----------------------------------------------------------------------------*/

#include <stdio.h>
#include <unistd.h>
#include <stdbool.h>
#include <stdlib.h>

typedef struct{
    char* filename;
    char* token;
    char* crn;
    char* url;
    char* channel;
    char *def;
    char *private;
    bool overwrite;

    bool set_token;
    bool set_crn;
} params;

params default_params(){
    params p;
    p.filename = "test.json";
    p.url = "https://cloud.ibm.com";
    p.channel = "ibm_quantum_platform";
    p.def = "false";
    p.private = "false";
    p.overwrite = false;

    p.set_token = false;
    p.set_crn = false;

    return p;
}

void write_json(params p){

    if (!p.set_token){
        fprintf(stderr, "Token not set!\n");
        exit(1);
    }

    if (!p.set_crn){
        fprintf(stderr, "CRN not set!\n");
        exit(1);
    }

    // Checking if file exists.
    if (!p.overwrite && access(p.filename, F_OK) == 0){
        fprintf(stderr, "Cannot overwrite existing file %s without permission (-o)!\n", p.filename);
        exit(1);
    }

    FILE *fptr;

    fptr = fopen(p.filename, "w");

    fprintf(fptr, "{\n\
    \"default-ibm-quantum-platform\": {\n\
        \"channel\": \"%s\",\n\
        \"instance\": \"%s\",\n\
        \"is_default_account\": %s,\n\
        \"private_endpoint\": %s,\n\
        \"token\": \"%s\",\n\
        \"url\": \"%s\"\n\
    }\n\
}", p.channel, p.crn, p.def, p.private, p.token, p.url);

    fclose(fptr);
}

void print_help(){
    char *help_str = "Qiskit Configuration: \n\
    -h	Prints help menu \n\
    -t	Specifies token \n\
    -i	Specifies instance / CRN (Cloud Resource Name) \n\
    -o	Overwrites existing file \n\
    -f	Specifies filename (default ~/.qiskit/qiskit-ibm.json) \n\
    -c	Specifies channel (default ibm_quantum_platform) \n\
    -d	Specifies default state (default false, flags true) \n\
    -p	Specifies private endpoint (default false, flags true) \n\
    -u	Specifies URL (default https://cloud.ibm.com) \n\
\n\
    t and i are required\n";

    printf(help_str);
}

void parse_args(int argc, char** argv){
    int opt;

    params p = default_params();

    while((opt = getopt(argc, argv, "ht:i:of:c:u:pd")) != -1){ 
        switch(opt){ 
            case 'h': 
                print_help();
                break;
            case 't': 
                p.token = optarg;
                p.set_token = true;
                printf("Setting token\n");
                break;
            case 'i': 
                p.crn = optarg;
                p.set_crn = true;
                printf("Setting instance / CRN\n");
                break;
            case 'o': 
                p.overwrite = true;
                printf("Overwriting existing file\n");
                break;
            case 'f': 
                p.filename = optarg;
                printf("Setting filename\n");
                break;
            case 'c': 
                p.channel = optarg;
                printf("Setting channel\n");
                break;
            case 'u': 
                p.url = optarg;
                printf("Setting url\n");
                break;
            case 'p': 
                p.private = "true";
                printf("Setting as private\n");
                break;
            case 'd': 
                p.def = "true";
                printf("Setting as default\n");
                break;
        } 
    } 

    write_json(p);
}

int main(int argc, char** argv){
    parse_args(argc, argv);
    return 0;
}
