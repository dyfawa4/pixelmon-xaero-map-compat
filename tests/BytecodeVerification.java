import java.nio.file.*;
import java.io.*;
import java.util.*;
import java.util.jar.*;
import javax.script.*;
import jdk.nashorn.api.scripting.ScriptObjectMirror;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;

/** Validate the final native edits and execute the shipped Forge JS transforms. */
public final class BytecodeVerification implements Opcodes {
    static int checks;
    static void check(boolean pass,String message){if(!pass)throw new AssertionError(message);checks++;}
    static ClassNode read(JarFile jar,String name)throws Exception {
        ClassNode c=new ClassNode();new ClassReader(jar.getInputStream(jar.getJarEntry(name))).accept(c,0);return c;
    }
    static void verify(ClassNode c)throws Exception {
        for(MethodNode m:c.methods)if((m.access&(ACC_ABSTRACT|ACC_NATIVE))==0)new Analyzer<BasicValue>(new BasicVerifier()).analyze(c.name,m);
    }
    public static void main(String[] args)throws Exception {
        try(JarFile mini=new JarFile(args[0]);JarFile world=new JarFile(args[1]);JarFile compass=new JarFile(args[2]);JarFile nature=new JarFile(args[3])){
            for(JarFile jar:List.of(mini,world)){
                Enumeration<JarEntry> entries=jar.entries();
                while(entries.hasMoreElements()){
                    JarEntry e=entries.nextElement();String n=e.getName();
                    if(n.endsWith(".class")&&(n.startsWith("xaero/pixelmon/")||n.startsWith("xaero/map/pixelmon/"))) {verify(read(jar,n));checks++;}
                }
            }
            for(String n:List.of("xaero/hud/minimap/radar/icon/cache/id/variant/RadarIconVariantHandler.class","xaero/hud/minimap/radar/icon/definition/RadarIconDefinitionManager.class","xaero/hud/minimap/radar/render/element/RadarRenderProvider.class","xaero/common/settings/ModSettings.class")){
                verify(read(mini,n));checks++;
            }
            verify(read(world,"xaero/map/mods/minimap/element/MinimapElementRendererWrapper.class"));checks++;
            ClassNode settings=read(mini,"xaero/common/settings/ModSettings.class");
            check(settings.fields.stream().anyMatch(f->f.name.equals("ENCHANT_COLORS")&&f.desc.equals("[Ljava/lang/String;")),"Legacy exact field ABI");
            ScriptEngine engine=new ScriptEngineManager().getEngineByName("nashorn");
            check(engine!=null,"Java 11 Forge-compatible JS engine");
            try(Reader js=new InputStreamReader(mini.getInputStream(mini.getJarEntry("coremods/pixelmon_compass.js")),java.nio.charset.StandardCharsets.UTF_8)){engine.eval(js);}
            ScriptObjectMirror transformers=(ScriptObjectMirror)((Invocable)engine).invokeFunction("initializeCoreMod");
            check(transformers.size()==3,"Three optional compass coremods");
            for(Object value:transformers.values()){
                ScriptObjectMirror spec=(ScriptObjectMirror)value;
                ScriptObjectMirror target=(ScriptObjectMirror)spec.get("target");
                String name=(String)target.get("class"),method=(String)target.get("methodName"),desc=(String)target.get("methodDesc");
                ClassNode c=read(name.contains("naturescompass")?nature:compass,name.replace('.','/')+".class");
                MethodNode m=c.methods.stream().filter(v->v.name.equals(method)&&v.desc.equals(desc)).findFirst().orElseThrow();
                ((ScriptObjectMirror)spec.get("transformer")).call(null,m);
                verify(c);checks++;
                boolean oldPalette=false,bridge=false;
                for(AbstractInsnNode n:m.instructions.toArray()){
                    if(n instanceof FieldInsnNode&&((FieldInsnNode)n).name.equals("ENCHANT_COLORS"))oldPalette=true;
                    if(n instanceof MethodInsnNode&&((MethodInsnNode)n).owner.startsWith("xaero/pixelmon/"))bridge=true;
                }
                check(bridge,"Compass callback reaches embedded bridge: "+method);
                if(method.equals("addPoint"))check(!oldPalette,"Old failing field no longer accessed by callback");
            }
            // Ask the JVM verifier to load modified classes with real dependencies, without initializing the game.
            for(String name:List.of("xaero.hud.minimap.radar.icon.cache.id.variant.RadarIconVariantHandler","xaero.hud.minimap.radar.icon.definition.RadarIconDefinitionManager","xaero.hud.minimap.radar.render.element.RadarRenderProvider","xaero.map.mods.minimap.element.MinimapElementRendererWrapper","xaero.pixelmon.CompassCompat")){
                Class.forName(name,false,BytecodeVerification.class.getClassLoader());checks++;
            }
        }
        System.out.println("PASS "+checks+" bytecode/coremod/JVM checks");
    }
}
