import java.util.ArrayList;
import java.util.List;  // This import is unused

public class Demo {
    
    public static void main(String[] args) {
        // This is a demo class with some Sonar issues
        boolean flag = true;
        
        if (flag == true) {  // java:S1125 - Boolean literal comparison
            System.out.println("Flag is true");
        }
        
        // java:S125 - Commented out code
        // System.out.println("This is commented out");
        
        // java:S1481 - Unused local variable
        String unused = "This variable is not used";
        
        // java:S3776 - Cognitive complexity
        complexMethod();
    }
    
    private static void complexMethod() {
        int x = 0;
        while (x < 10) {
            if (x % 2 == 0) {
                System.out.println("Even");
            } else if (x % 3 == 0) {
                System.out.println("Divisible by 3");
            } else if (x % 5 == 0) {
                System.out.println("Divisible by 5");
            } else {
                System.out.println("Other");
            }
            x++;
        }
    }
}
