#include <libvirt/libvirt.h>
#include <libvirt/virterror.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define BUFLEN 1024

void read_stream(virStreamPtr stream, int events, void* opaque) {
	(void)events, (void)opaque;
	char buf[BUFLEN];
	int ret = virStreamRecv(stream,buf,BUFLEN);
	printf("ret=%d\n",ret);
	/*if(ret<0)
	  return;
	  else if(ret==0) {
	  virStreamFinish(stream);
	  return;
	  }
	  else if(!fwrite(buf,sizeof(char),ret,stdout))
	  virStreamFinish(stream);*/
	ret = fwrite(buf,sizeof(char),ret,stdout);
	printf("ret=%d\n",ret);
}

void write_stream(virStreamPtr stream, int events, void* opaque) {
	(void)events, (void)opaque;
	char buf[BUFLEN];
	char* ret = fgets(buf,BUFLEN,stdin);
	printf("ret=%s\n",ret);
	virStreamSend(stream,buf,strlen(buf));
}

/*void error_handler(void* data,virErrorPtr error) {
printf("error");
}*/
int handler(virStreamPtr stream,const char* data, size_t nbytes,void* opaque) {
	return fwrite(data,sizeof(char),nbytes,stdout);
}

int main(void) {
	virConnectPtr conn = virConnectOpen(NULL);
	//virConnSetErrorFunc(conn,NULL,error_handler);
	virDomainPtr dom = virDomainLookupByName(conn,"bob");
	virStreamPtr stream = virStreamNew(conn,0);
	int state, reason;
	virDomainGetState(dom,&state,&reason,0);
	if(state != VIR_DOMAIN_SHUTOFF) {
		virDomainDestroy(dom);
	}
	virDomainCreate(dom);
	virDomainOpenConsole(dom,NULL,stream,0);
	virStreamRecvAll(stream,handler,NULL);
	//virEventAddHandle(STDIN_FILENO, VIR_EVENT_HANDLE_READABLE, stdin_handler,NULL,NULL);
	//virStreamEventAddCallback(stream,VIR_STREAM_EVENT_READABLE,read_stream,NULL,NULL);
	//virStreamEventAddCallback(stream,VIR_STREAM_EVENT_WRITABLE,write_stream,NULL,NULL);
	return 0;
}
